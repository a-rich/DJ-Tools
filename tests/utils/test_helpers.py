"""Testing for the helpers module."""
from datetime import datetime
from pathlib import Path
import logging
from typing import Optional
from unittest import mock

import pytest
from pydub import AudioSegment, generators

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
    trim_initial_silence,
)


@pytest.mark.parametrize("track_a", ["some track", "another track"])
@pytest.mark.parametrize("track_b", ["some track", "another track"])
def test_compute_distance(track_a, track_b):
    """Test for the compute_distance function."""
    ret = compute_distance(
        "playlist",
        track_a,
        track_b,
        100,
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
    config.CHECK_TRACKS_FUZZ_RATIO = 100
    expected_matches = [
        "track 1 - someone unique",
        "track 2 - seen them before",
    ]
    matches = find_matches(
        spotify_tracks={
            "playlist_a": expected_matches,
            "playlist_b": [
                "track 3 - special person",
                "track 4 - seen them before",
            ],
        },
        beatcloud_tracks=[
            "track 5 - who's that?",
        ]
        + expected_matches,
        config=config,
    )
    assert all(
        match[-1] == config.CHECK_TRACKS_FUZZ_RATIO for match in matches
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
        ],
    ],
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


def test_get_local_tracks_dir_does_not_exist(config, caplog):
    """Test for the get_local_tracks function."""
    caplog.set_level("INFO")
    local_dir = Path("not-a-real-dir")
    config.LOCAL_DIRS = [local_dir]
    local_dir_tracks = get_local_tracks(config)
    assert caplog.records[0].message == (
        f"{local_dir.as_posix()} does not exist; will not be able to check "
        "its contents against the beatcloud"
    )
    assert not local_dir_tracks
    assert caplog.records[1].message == "Got 0 files under local directories"


def test_get_local_tracks_dir_does_exist(tmpdir, config, caplog):
    """Test for the get_local_tracks function."""
    caplog.set_level("INFO")
    check_dirs = []
    tmpdir = Path(tmpdir)
    for _dir in ["dir1", "dir2"]:
        path = tmpdir / _dir
        path.mkdir(parents=True, exist_ok=True)
        check_dirs.append(path)
    config.LOCAL_DIRS = check_dirs
    beatcloud_tracks = ["test_file1.mp3", "test_file2.mp3"]
    for index, track in enumerate(beatcloud_tracks):
        with open(
            check_dirs[index % len(check_dirs)] / f"{track}",
            mode="w",
            encoding="utf-8",
        ) as _file:
            _file.write("")
    local_dir_tracks = get_local_tracks(config)
    assert set(local_dir_tracks).union(set(check_dirs)) == set(check_dirs)
    assert (
        caplog.records[0].message
        == f"Got {len(check_dirs)} files under local directories"
    )


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
    "djtools.spotify.helpers.spotipy.Spotify.playlist", side_effect=Exception()
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


@mock.patch("djtools.utils.helpers.get_spotify_client", new=mock.Mock())
@mock.patch(
    "djtools.utils.helpers.get_playlist_ids",
    new=mock.Mock(
        return_value={"r/techno | Top weekly Posts": "5gex4eBgWH9nieoVuV8hDC"}
    ),
)
def test_get_spotify_tracks_no_matching_playlist_id(config, caplog):
    """Test for the get_spotify_tracks function."""
    caplog.set_level("ERROR")
    playlist = "not-a-real-playlist"
    get_spotify_tracks(config, [playlist])
    assert (
        caplog.records[0].message
        == f"{playlist} not in spotify_playlists.yaml"
    )


@pytest.mark.parametrize("verbosity", [0, 1])
@mock.patch("djtools.utils.helpers.get_spotify_client", new=mock.Mock())
@mock.patch(
    "djtools.utils.helpers.get_playlist_ids",
    new=mock.Mock(
        return_value={"r/techno | Top weekly Posts": "5gex4eBgWH9nieoVuV8hDC"}
    ),
)
@mock.patch(
    "djtools.utils.helpers.get_playlist_tracks",
    return_value={"some track - some artist"},
)
def test_get_spotify_tracks(
    mock_get_playlist_tracks, config, verbosity, caplog
):
    """Test for the get_spotify_tracks function."""
    caplog.set_level("INFO")
    config.VERBOSITY = verbosity
    tracks = get_spotify_tracks(config, ["r/techno | Top weekly Posts"])
    assert isinstance(tracks, dict)
    assert caplog.records[0].message == (
        'Got 1 track from Spotify playlist "r/techno | Top weekly Posts"'
    )
    if verbosity:
        assert caplog.records[1].message == "\tsome track - some artist"
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
        ({}, type(None), type(None)),
    ],
)
def test_make_path_decorator(kwargs, expected_str_kwarg, expected_path_kwarg):
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
    def foo(
        path_arg: Path, path_kwarg: Path
    ):  # pylint: disable=disallowed-name
        assert isinstance(path_arg, Path)
        assert isinstance(path_kwarg, Path)

    with pytest.raises(
        RuntimeError,
        match=expected,
    ):
        foo(arg, path_kwarg=kwarg)


def test_reverse_title_and_artist():
    """Test for the reverse_title_and_artist function."""
    path_lookup = {
        "title - artist": "path/to/title - artist.mp3",
        "multiple - hyphens - artist": "path/to/multiple - hyphens - artist.mp3",
    }
    expected = {
        "artist - title": "path/to/title - artist.mp3",
        "artist - multiple - hyphens": "path/to/multiple - hyphens - artist.mp3",
    }
    new_path_lookup = reverse_title_and_artist(path_lookup)
    assert new_path_lookup == expected


def test_trim_initial_silence():
    """Test for the trim_initial_silence function."""
    leading_silence = 5000
    silence_len = 500
    track_durations = [12345, 23456, 34567]
    audio = AudioSegment.silent(duration=leading_silence)
    for dur in track_durations:
        audio += generators.WhiteNoise().to_audio_segment(duration=dur)
        audio += AudioSegment.silent(duration=silence_len)

    track_durations = [dur + silence_len for dur in track_durations]
    assert len(audio) == leading_silence + sum(track_durations)
    audio = trim_initial_silence(audio, track_durations)
    assert len(audio) == sum(track_durations) + silence_len
