from unittest import mock

import pytest

from djtools.spotify.helpers import (
    add_tracks,
    compute_distance,
    get_playlist_ids,
    get_spotify_client,
    find_matches,
    get_playlist_tracks,
    get_spotify_tracks,
)
from test_data import MockOpen


pytest_plugins = [
    "test_data",
]


@mock.patch("djtools.spotify.spotify_playlist_builder.spotipy.Spotify")
def test_get_spotify_client(test_config):
    test_config["SPOTIFY_CLIENT_ID"] = "test_client_id"
    test_config["SPOTIFY_CLIENT_SECRET"] = "test_client_secret"
    test_config["SPOTIFY_REDIRECT_URI"] = "test_redirect_uri"
    get_spotify_client(test_config)


def test_get_spotify_clientmissing_spotify_configs(test_config):
    del test_config["SPOTIFY_CLIENT_ID"]
    with pytest.raises(
        KeyError,
        match="Using the spotify package requires the following config "
            "options: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, "
            "SPOTIFY_REDIRECT_URI"
    ):
        get_spotify_client(test_config)
        

def test_get_spotify_client_bad_spotify_configs(test_config):
    with pytest.raises(
        Exception,
        match="Failed to instantiate the Spotify client",
    ):
        get_spotify_client(test_config)


def test_get_playlist_ids():
    playlist_ids = get_playlist_ids()
    assert isinstance(playlist_ids, dict)


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


@mock.patch("djtools.spotify.helpers.spotipy.Spotify")
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.next",
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
    "djtools.spotify.helpers.spotipy.Spotify.playlist",
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


@mock.patch("djtools.spotify.helpers.spotipy.Spotify")
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.playlist",
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
    files=["spotify_playlists.json"],
    content='{"r/techno | Top weekly Posts": "5gex4eBgWH9nieoVuV8hDC"}',
).open)
@mock.patch(
    "djtools.spotify.helpers.get_playlist_tracks",
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
        "playlist A not in spotify_playlists.json"
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
        match="Using the spotify package requires the following config "
            "options: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, "
            "SPOTIFY_REDIRECT_URI"
    ):
        get_spotify_tracks(test_config)
