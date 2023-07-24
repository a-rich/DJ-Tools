"""Testing for the helpers module."""
from datetime import datetime
from pathlib import Path
import logging
from typing import Optional
from unittest import mock

import pytest

from djtools.utils.helpers import (
    compute_distance,
    find_matches,
    get_beatcloud_tracks,
    get_local_tracks,
    get_playlist_tracks,
    get_spotify_tracks,
    initialize_logger,
    make_path,
    reverse_title_and_artist,
)

from ..test_utils import MockOpen


@pytest.mark.parametrize("track_a", ["some track", "another track"])
@pytest.mark.parametrize("track_b", ["some track", "another track"])
def test_compute_distance(track_a, track_b):
    """Test for the compute_distance function."""
    ret = compute_distance(
        "playlist",
        track_a,
        track_b,
        99,
    )
    if track_a == track_b:
        assert ret
        assert ret[0] == "playlist"
        assert ret[1] == track_a
        assert ret[2] == track_b
        assert ret[3] == 100
    else:
        assert not ret


def test_find_matches(config):
    """Test for the find_matches function."""
    config.CHECK_TRACKS_FUZZ_RATIO = 99
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
        config=config,
    )
    assert all(
        match[-1] >= config.CHECK_TRACKS_FUZZ_RATIO
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
@mock.patch("djtools.utils.helpers.check_output")
def test_get_beatcloud_tracks(mock_os_popen, proc_dump):
    """Test for the get_beatcloud_tracks function."""
    proc_dump = list(map(Path, proc_dump))
    mock_os_popen.return_value = b"\n".join(
        map(lambda x: x.as_posix().encode(), proc_dump)
    )
    tracks = get_beatcloud_tracks()
    mock_os_popen.assert_called_once()
    assert len(tracks) == len(proc_dump)
    for track, line in zip(tracks, proc_dump):
        assert track == line


def test_get_local_tracks(tmpdir, config):
    """Test for the get_local_tracks function."""
    check_dirs = []
    tmpdir = Path(tmpdir)
    for _dir in ["dir1", "dir2"]:
        path = tmpdir / _dir
        path.mkdir(parents=True, exist_ok=True)
        check_dirs.append(path)
    config.LOCAL_DIRS = check_dirs + [Path("nonexistent_dir")]
    beatcloud_tracks = ["test_file1.mp3", "test_file2.mp3"]
    for index, track in enumerate(beatcloud_tracks):
        with open(
            check_dirs[index % len(check_dirs)] / f"{track}",
            mode="w",
            encoding="utf-8",
        ) as _file:
            _file.write("")
    local_dir_tracks = get_local_tracks(config)
    assert all(x in local_dir_tracks for x in check_dirs)
    assert len(local_dir_tracks) == len(check_dirs)


def test_get_local_tracks_empty(tmpdir, config, caplog):
    """Test for the get_local_tracks function."""
    caplog.set_level("INFO")
    config.LOCAL_DIRS = [Path(tmpdir)]
    local_dir_tracks = get_local_tracks(config)
    assert not local_dir_tracks
    assert caplog.records[0].message == "Got 0 files under local directories"


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
    """Test for the get_playlist_tracks function."""
    mock_spotipy.playlist.return_value = mock_spotipy_playlist.return_value
    mock_spotipy.next.return_value = mock_spotipy_next.return_value
    expected = list(mock_spotipy_playlist.return_value["tracks"]["items"])
    expected.extend(list(mock_spotipy_next.return_value["items"]))
    tracks = get_playlist_tracks(mock_spotipy, "some ID")
    assert tracks == expected


@mock.patch("djtools.spotify.helpers.spotipy.Spotify")
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.playlist",
    side_effect=Exception()
)
def test_get_playlist_tracks_handles_spotipy_exception(
    mock_spotipy_playlist, mock_spotipy
):
    """Test for the get_playlist_tracks function."""
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
    mock_get_playlist_tracks, config, verbosity, caplog
):
    """Test for the get_spotify_tracks function."""
    caplog.set_level("INFO")
    config.SPOTIFY_CLIENT_ID = "spotify client ID"
    config.SPOTIFY_CLIENT_SECRET = "spotify client secret"
    config.SPOTIFY_REDIRECT_URI = "spotify redirect uri"
    config.CHECK_TRACKS_SPOTIFY_PLAYLISTS = [
        "playlist A", "r/techno | Top weekly Posts"
    ]
    config.VERBOSITY = verbosity
    tracks = get_spotify_tracks(config, config.CHECK_TRACKS_SPOTIFY_PLAYLISTS)
    assert isinstance(tracks, dict)
    assert caplog.records[0].message == (
        "playlist A not in spotify_playlists.yaml"
    )
    assert caplog.records[1].message == (
        'Got 1 track from Spotify playlist "r/techno | Top weekly Posts"'
    )
    if verbosity:
        assert caplog.records[2].message == "\tsome track - some artist"
    mock_get_playlist_tracks.assert_called_once()


def test_initialize_logger():
    """Test for the intitialize_logger function."""
    today = f'{datetime.now().strftime("%Y-%m-%d")}.log'
    logger, log_file = initialize_logger()
    assert isinstance(logger, logging.Logger)
    assert log_file.name == today


@pytest.mark.parametrize(
    "kwargs, expected_str_kwarg, expected_path_kwarg",
    [
        ({"str_kwarg": "string kwarg", "path_kwarg": "path kwarg"}, str, Path),
        ({}, type(None), type(None))
    ]
)
def test_make_path_decorator(
    kwargs, expected_str_kwarg, expected_path_kwarg
):
    """Test for the make_path decorator function."""
    @make_path
    def foo(  # pylint: disable=disallowed-name
            str_arg: str,
            path_arg: Path,
            str_kwarg: Optional[str] = None,
            path_kwarg: Optional[Path] = None,
    ):
        assert isinstance(str_arg, str)
        assert isinstance(path_arg, Path)
        assert isinstance(str_kwarg, expected_str_kwarg)
        assert isinstance(path_kwarg, expected_path_kwarg)

    foo("a string arg", "a string arg path", **kwargs)


@pytest.mark.parametrize(
    "arg, kwarg, expected",
    [
        (1, "", 'Error creating Path in function "foo" from positional'),
        ("", 1, 'Error creating Path in function "foo" from keyword'),
    ],
)
def test_make_path_decorator_raises_error(arg, kwarg, expected):
    """Test for the make_path decorator function."""
    @make_path
    def foo(path_arg: Path, path_kwarg: Path):  # pylint: disable=disallowed-name
        assert isinstance(path_arg, Path)
        assert isinstance(path_kwarg, Path)

    with pytest.raises(
        RuntimeError,
        match=expected,
    ):
        foo(arg, path_kwarg=kwarg)


def test_reverse_title_and_artist():
    """Test for the reverse_title_and_artist function."""
    path_lookup = {"title - artist": "path/to/title - artist.mp3"}
    expected = {"artist - title": "path/to/title - artist.mp3"}
    new_path_lookup = reverse_title_and_artist(path_lookup)
    assert new_path_lookup == expected
