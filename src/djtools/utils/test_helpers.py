from datetime import datetime
import os
import logging
from unittest import mock

import pytest

from djtools.utils.helpers import (
    add_tracks,
    compute_distance,
    catch,
    find_matches,
    initialize_logger,
    get_beatcloud_tracks,
    get_local_tracks,
    get_playlist_tracks,
    get_spotify_tracks,
    make_dirs,
    raise_,
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


def test_catch():
    x = "test"
    func = lambda x: x
    assert catch(func, x) == func(x)
    func = lambda x: x/0
    ret = catch(func, x)
    assert ret is None
    handler_ret = "some string"
    handler = lambda x: handler_ret
    ret = catch(func, x, handle=handler)
    assert ret == handler_ret


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
    test_config.CHECK_TRACKS_FUZZ_RATIO = 99
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
        match[-1] >= test_config.CHECK_TRACKS_FUZZ_RATIO
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
        assert track == line


def test_get_local_tracks(tmpdir, test_config):
    check_dirs = []
    for dir in ["dir1", "dir2"]:
        path = os.path.join(tmpdir, dir).replace(os.sep, "/")
        os.makedirs(path)
        check_dirs.append(path)
    test_config.CHECK_TRACKS_LOCAL_DIRS = check_dirs + ["nonexistent_dir"]
    beatcloud_tracks = ["test_file1.mp3", "test_file2.mp3"]
    for index, track in enumerate(beatcloud_tracks):
        with open(
            os.path.join(
                check_dirs[index % len(check_dirs)], f"{track}"
            ).replace(os.sep, "/"),
            mode="w",
            encoding="utf-8",
        ) as _file:
            _file.write("")
    local_dir_tracks = get_local_tracks(test_config)
    assert all(x in local_dir_tracks for x in check_dirs)
    assert len(local_dir_tracks) == len(check_dirs)


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
    files=["spotify_playlists.yaml"],
    content='{"r/techno | Top weekly Posts": "5gex4eBgWH9nieoVuV8hDC"}',
).open)
@mock.patch(
    "djtools.utils.helpers.get_playlist_tracks",
    return_value={"some track - some artist"},
)
def test_get_spotify_tracks(
    mock_get_playlist_tracks, test_config, verbosity, caplog
):
    caplog.set_level("INFO")
    test_config.SPOTIFY_CLIENT_ID = "spotify client ID"
    test_config.SPOTIFY_CLIENT_SECRET = "spotify client secret"
    test_config.SPOTIFY_REDIRECT_URI = "spotify redirect uri"
    test_config.CHECK_TRACKS_SPOTIFY_PLAYLISTS = [
        "playlist A", "r/techno | Top weekly Posts"
    ]
    test_config.VERBOSITY = verbosity
    tracks = get_spotify_tracks(test_config)
    assert isinstance(tracks, dict)
    assert caplog.records[0].message == (
        "playlist A not in spotify_playlists.yaml"
    )
    assert caplog.records[1].message == (
        'Getting tracks from Spotify playlist "r/techno | Top weekly Posts"...'
    )
    assert caplog.records[2].message == "Got 1 track"
    if verbosity:
        assert caplog.records[3].message == "\tsome track - some artist"
    mock_get_playlist_tracks.assert_called_once()


def test_initialize_logger():
    today = f'{datetime.now().strftime("%Y-%m-%d")}.log'
    logger, log_file = initialize_logger()
    assert isinstance(logger, logging.Logger)
    assert os.path.basename(log_file) == today


@pytest.mark.parametrize("platform", ["posix", "nt"])
def test_make_dirs(tmpdir, platform):
    with mock.patch("djtools.utils.helpers.os_name", platform):
        new_dir = os.path.join(tmpdir, "test_dir").replace(os.sep, "/")
        make_dirs(new_dir)
        assert os.path.exists(new_dir)
        new_sub_dir = os.path.join(
            tmpdir, "test_dir_2", "sub_dir"
        ).replace(os.sep, "/")
        make_dirs(new_sub_dir)
        assert os.path.exists(new_sub_dir)
        rel_dir = os.path.join(tmpdir, "relative_dir").replace(os.sep, "/")
        make_dirs(rel_dir)
        assert os.path.exists(rel_dir)


def test_raise_():
    with pytest.raises(Exception):
        raise_(Exception())
