import os
from unittest import mock

import pytest

from djtools.spotify.spotify_playlist_checker import (
    add_tracks,
    check_playlists,
    compute_distance,
    find_matches,
    get_beatcloud_tracks,
    get_playlist_tracks,
    get_spotify_tracks,
)
from test_data import MockOpen


pytest_plugins = [
    "test_data",
]


def test_add_tracks():
    test_input = {
        "items": [
            {
                "track": {
                    "name": "track title",
                    "artists": [ 
                        {"name": "artist name"},
                    ],
                },
            },
            {
                "track": {
                    "name": "another track title",
                    "artists": [ 
                        {"name": "another artist name"},
                        {"name": "a second artist name"},
                    ],
                },
            },
        ],
    }
    expected = [
        "track title - artist name",
        "another track title - another artist name, a second artist name"
    ]
    output = add_tracks(test_input)
    assert output == expected


@pytest.mark.parametrize("get_spotify_tracks_flag", [True, False])
@pytest.mark.parametrize(
    "beatcloud_tracks", [[], ["track title - artist name"]]
)
@mock.patch(
    "djtools.spotify.spotify_playlist_checker.get_beatcloud_tracks",
    return_value=["track title - artist name"],
)
@mock.patch(
    "djtools.spotify.spotify_playlist_checker.get_spotify_tracks",
    return_value={"playlist": ["track title - artist name"]},
)
def test_check_playlists(
    mock_get_spotify_tracks,
    mock_get_beatcloud_tracks,
    test_config,
    get_spotify_tracks_flag,
    beatcloud_tracks,
    caplog,
):
    caplog.set_level("INFO")
    if not get_spotify_tracks_flag:
        mock_get_spotify_tracks.return_value = []
    ret_beatcloud_tracks = check_playlists(test_config, beatcloud_tracks)
    if not get_spotify_tracks_flag:
        record = caplog.records.pop(0)
        assert record.message == (
            "There are no Spotify tracks; make sure SPOTIFY_CHECK_PLAYLISTS "
            "has one or more keys from playlist_checker.json"
        )
    else:
        if not beatcloud_tracks:
            assert (
                ret_beatcloud_tracks ==
                mock_get_beatcloud_tracks.return_value
            )
        assert caplog.records[0].message == (
            "Spotify playlist(s) / beatcloud matches: "
            f"{len(mock_get_spotify_tracks.return_value)}"
        )
        assert caplog.records[1].message == "playlist:"
        assert caplog.records[2].message == (
            "\t100: track title - artist name | track title - artist name"
        )


@pytest.mark.parametrize("track_a", ["some track", "another track"])
@pytest.mark.parametrize("track_b", ["some track", "another track"])
def test_compute_distance(track_a, track_b):
    ret = compute_distance(
        "playlist",
        track_a,
        track_b,
        99,
    )
    if track_a == track_b:
        assert ret
        playlist, ret_track_a, ret_track_b, fuzz_ratio = ret
        assert playlist == "playlist"
        assert ret_track_a == track_a
        assert ret_track_b == track_b
        assert fuzz_ratio == 100
    else:
        assert not ret


def test_find_matches(test_config):
    test_config["CHECK_TRACK_OVERLAP_FUZZ_RATIO"] = 99
    expected_matches = [
        "track 1 - someone unique",
        "track 2 - seen them before",
    ]
    matches = find_matches(
        spotify_tracks={
            "playlist_A": expected_matches,
            "playlist_b": [
                "track 3 - special person", "track 4 - seen them before"
            ],
        },
        beatcloud_tracks=[
            "track 99 - who's that?",
        ] + expected_matches,
        config=test_config,
    )
    assert all(
        match[-1] >= test_config["CHECK_TRACK_OVERLAP_FUZZ_RATIO"]
        for match in matches
    )
    assert len(matches) == 2
    assert [x[1] for x in matches] == expected_matches


@pytest.mark.parametrize(
    "proc_dump",
    [
        [],
        [
            "aweeeezy/Bass/2022-12-21/track - artist.mp3",
            "aweeeezy/Techno/2022-12-21/track - artist.mp3",
        ]
    ]
)
@mock.patch("os.popen")
def test_get_beatcloud_tracks(mock_os_popen, proc_dump):
    process = mock_os_popen.return_value.__enter__.return_value
    process.read.side_effect = lambda: "\n".join(proc_dump)
    tracks = get_beatcloud_tracks()
    mock_os_popen.assert_called_once()
    assert len(tracks) == len(proc_dump)
    for track, line in zip(tracks, proc_dump):
        assert track == os.path.splitext(os.path.basename(line))[0]


@mock.patch("djtools.spotify.spotify_playlist_checker.spotipy.Spotify")
@mock.patch(
    "djtools.spotify.spotify_playlist_checker.spotipy.Spotify.next",
    return_value={
        "items": [
            {
                "track": {
                    "name": "last track title",
                    "artists": [ 
                        {"name": "final artist name"},
                    ],
                },
            },
        ],
        "next": False,
    },
)
@mock.patch(
    "djtools.spotify.spotify_playlist_checker.spotipy.Spotify.playlist",
    return_value={
        "tracks": {
            "items": [
                {
                    "track": {
                        "name": "track title",
                        "artists": [ 
                            {"name": "artist name"},
                        ],
                    },
                },
                {
                    "track": {
                        "name": "another track title",
                        "artists": [ 
                            {"name": "another artist name"},
                            {"name": "a second artist name"},
                        ],
                    },
                },
            ],
            "next": True,
        },
    },
)
def test_get_playlist_tracks(
    mock_spotipy_playlist, mock_spotipy_next, mock_spotipy
):
    mock_spotipy.playlist.return_value = mock_spotipy_playlist.return_value
    mock_spotipy.next.return_value = mock_spotipy_next.return_value
    expected = sorted(set([
        "track title - artist name",
        "another track title - another artist name, a second artist name",
        "last track title - final artist name"
    ]))
    tracks = sorted(get_playlist_tracks(mock_spotipy, "some ID"))
    assert tracks == expected


@mock.patch("djtools.spotify.spotify_playlist_checker.spotipy.Spotify")
@mock.patch(
    "djtools.spotify.spotify_playlist_checker.spotipy.Spotify.playlist",
    side_effect=Exception()
)
def test_get_playlist_tracks_handles_spotipy_exception(
    mock_spotipy_playlist, mock_spotipy
):
    test_playlist_id = "some ID"
    mock_spotipy.playlist.side_effect = mock_spotipy_playlist.side_effect
    with pytest.raises(
        Exception, match=f"Failed to get playlist with ID {test_playlist_id}"
    ):
        get_playlist_tracks(mock_spotipy, test_playlist_id)


@pytest.mark.parametrize("verbosity", [0, 1])
@mock.patch("builtins.open", MockOpen(
    files=["playlist_checker.json"],
    content='{"r/techno | Top weekly Posts": "5gex4eBgWH9nieoVuV8hDC"}',
).open)
@mock.patch(
    "djtools.spotify.spotify_playlist_checker.get_playlist_tracks",
    return_value={"some track - some artist"},
)
def test_get_spotify_tracks(
    mock_get_playlist_tracks, test_config, verbosity, caplog
):
    caplog.set_level("INFO")
    test_config["SPOTIFY_CLIENT_ID"] = "spotify client ID"
    test_config["SPOTIFY_CLIENT_SECRET"] = "spotify client secret"
    test_config["SPOTIFY_REDIRECT_URI"] = "spotify redirect uri"
    test_config["SPOTIFY_CHECK_PLAYLISTS"] = [
        "playlist A", "r/techno | Top weekly Posts"
    ]
    test_config["VERBOSITY"] = verbosity
    tracks = get_spotify_tracks(test_config)
    assert isinstance(tracks, dict)
    assert caplog.records[0].message == (
        "playlist A not in playlist_checker.json"
    )
    assert caplog.records[1].message == (
        'Getting tracks from Spotify playlist "r/techno | Top weekly Posts"...'
    )
    assert caplog.records[2].message == "Got 1 track"
    if verbosity:
        assert caplog.records[3].message == "\tsome track - some artist"
    mock_get_playlist_tracks.assert_called_once()


def test_get_spotify_tracks_no_spotify_creds(test_config):
    del test_config["SPOTIFY_CLIENT_ID"]
    del test_config["SPOTIFY_CLIENT_SECRET"]
    del test_config["SPOTIFY_REDIRECT_URI"]
    with pytest.raises(
        KeyError,
        match="Using the playlist_checker module requires the following "
            "config options: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, "
            "SPOTIFY_REDIRECT_URI"
    ):
        get_spotify_tracks(test_config)
