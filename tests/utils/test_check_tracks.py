"""Testing for the check_tracks module."""

from pathlib import Path
from unittest import mock

import pytest

from djtools.utils.check_tracks import compare_tracks


@pytest.mark.parametrize("download_from_spotify", [False, True])
@mock.patch(
    "djtools.utils.check_tracks.get_beatcloud_tracks",
    new=mock.Mock(return_value=[]),
)
@mock.patch(
    "djtools.utils.check_tracks.get_spotify_tracks",
    new=mock.Mock(return_value=[]),
)
@mock.patch("djtools.utils.check_tracks.get_local_tracks")
@mock.patch("djtools.utils.helpers.get_spotify_client", new=mock.Mock())
def test_compare_tracks_ignores_local_dirs_with_download_spotify_playlist(
    mock_get_local_tracks, download_from_spotify, config
):
    """Test the compare_tracks function."""
    if download_from_spotify:
        config.sync.download_spotify_playlist = "test-playlist"
    else:
        config.sync.download_spotify_playlist = ""
    local_dirs = [Path("some/dir")]
    config.utils.local_dirs = local_dirs
    mock_get_local_tracks.return_value = []
    compare_tracks(config)
    if download_from_spotify:
        mock_get_local_tracks.assert_not_called()
    else:
        mock_get_local_tracks.assert_called_once()
    assert config.utils.local_dirs == local_dirs


@mock.patch(
    "djtools.utils.check_tracks.find_matches",
    new=mock.Mock(return_value=[]),
)
@mock.patch(
    "djtools.utils.check_tracks.get_beatcloud_tracks",
    new=mock.Mock(return_value=[]),
)
@mock.patch(
    "djtools.utils.check_tracks.get_spotify_tracks",
    new=mock.Mock(return_value={}),
)
@pytest.mark.parametrize("downloading_instead_of_checking", [True, False])
def test_compare_tracks_get_spotify_tracks_no_tracks(
    downloading_instead_of_checking, config, caplog
):
    """Test the compare_tracks function."""
    caplog.set_level("WARNING")
    if downloading_instead_of_checking:
        config.sync.download_spotify_playlist = "test-playlist"
    else:
        config.utils.check_tracks_spotify_playlists = ["test-playlist"]
    beatcloud_tracks, beatcloud_matches = compare_tracks(config)
    if downloading_instead_of_checking:
        assert (
            "download_spotify_playlist is a key" in caplog.records[0].message
        )
    else:
        assert (
            "check_tracks_spotify_playlists has one or more keys"
            in caplog.records[0].message
        )
    assert not beatcloud_tracks
    assert not beatcloud_matches


@pytest.mark.parametrize("artist_first", [False, True])
@mock.patch("djtools.utils.check_tracks.find_matches")
@mock.patch("djtools.utils.check_tracks.get_beatcloud_tracks")
@mock.patch("djtools.utils.check_tracks.get_spotify_tracks")
def test_compare_tracks_get_spotify_tracks_yields_tracks(
    mock_get_spotify_tracks,
    mock_get_beatcloud_tracks,
    mock_find_matches,
    artist_first,
    config,
    caplog,
):
    """Test the compare_tracks function."""
    caplog.set_level("INFO")
    config.utils.check_tracks_spotify_playlists = ["test-playlist"]
    config.sync.artist_first = artist_first
    title = "title"
    artist = "artist"
    get_spotify_tracks_result = {
        "test-playlist": [
            {"track": {"name": title, "artists": [{"name": artist}]}}
        ]
    }
    expected_match = (
        f"{artist} - {title}" if artist_first else f"{title} - {artist}"
    )
    find_matches_result = [
        ("test-playlist", expected_match, expected_match, 100)
    ]
    expected_matches = [Path(f"{expected_match}.mp3")]
    mock_get_spotify_tracks.return_value = get_spotify_tracks_result
    mock_find_matches.return_value = find_matches_result
    mock_get_beatcloud_tracks.return_value = expected_matches
    beatcloud_tracks, beatcloud_matches = compare_tracks(config)
    assert (
        caplog.records[0].message
        == "\nSpotify Playlist Tracks / Beatcloud Matches: 1"
    )
    assert caplog.records[1].message == "test-playlist:"
    assert (
        caplog.records[2].message
        == f"\t100: {expected_match} | {expected_match}"
    )
    assert beatcloud_tracks == mock_get_beatcloud_tracks.return_value
    assert beatcloud_matches == expected_matches


@mock.patch(
    "djtools.utils.check_tracks.find_matches",
    new=mock.Mock(return_value=[]),
)
@mock.patch(
    "djtools.utils.check_tracks.get_beatcloud_tracks",
    new=mock.Mock(return_value=[]),
)
@mock.patch(
    "djtools.utils.check_tracks.get_local_tracks",
    new=mock.Mock(return_value={}),
)
def test_compare_tracks_get_local_tracks_no_tracks(config, caplog):
    """Test the compare_tracks function."""
    caplog.set_level("WARNING")
    config.utils.local_dirs = [Path("some/dir")]
    beatcloud_tracks, beatcloud_matches = compare_tracks(config)
    assert caplog.records[0].message == (
        "There are no local tracks; make sure local_dirs has one or "
        "more directories containing one or more tracks"
    )
    assert not beatcloud_tracks
    assert not beatcloud_matches


@pytest.mark.parametrize("artist_first", [False, True])
@mock.patch("djtools.utils.check_tracks.find_matches")
@mock.patch("djtools.utils.check_tracks.get_beatcloud_tracks")
@mock.patch("djtools.utils.check_tracks.get_local_tracks")
@mock.patch("djtools.utils.check_tracks.reverse_title_and_artist")
def test_compare_tracks_get_local_tracks_yields_tracks(
    mock_reverse_title_and_artist,
    mock_get_local_tracks,
    mock_get_beatcloud_tracks,
    mock_find_matches,
    artist_first,
    config,
):
    """Test the compare_tracks function."""
    local_dir = Path("some/dir")
    config.utils.local_dirs = [local_dir]
    config.sync.artist_first = artist_first
    file_stem = "artist - title" if artist_first else "title - artist"
    mock_get_local_tracks.return_value = {
        local_dir: [Path(f"{file_stem}.mp3")]
    }
    mock_get_beatcloud_tracks.return_value = [Path(f"{file_stem}.mp3")]
    find_matches_result = [(local_dir, file_stem, file_stem, 100)]
    mock_find_matches.return_value = find_matches_result
    compare_tracks(config)
    if artist_first:
        mock_reverse_title_and_artist.assert_called_once()
    else:
        mock_reverse_title_and_artist.assert_not_called()


@pytest.mark.parametrize(
    "beatcloud_tracks", [[Path("title - artist.mp3")], []]
)
@mock.patch("djtools.utils.check_tracks.get_beatcloud_tracks")
@mock.patch(
    "djtools.utils.check_tracks.get_spotify_tracks",
    new=mock.Mock(
        return_value={
            "test-playlist": [
                {"track": {"name": "title", "artists": [{"name": "artist"}]}}
            ]
        }
    ),
)
@mock.patch(
    "djtools.utils.check_tracks.find_matches",
    new=mock.Mock(return_value=[]),
)
def test_compare_tracks_cached_get_beatcloud_tracks(
    mock_get_beatcloud_tracks, beatcloud_tracks, config
):
    """Test the compare_tracks function."""
    config.utils.check_tracks_spotify_playlists = ["test-playlist"]
    compare_tracks(config, beatcloud_tracks)
    if beatcloud_tracks:
        mock_get_beatcloud_tracks.assert_not_called()
    else:
        mock_get_beatcloud_tracks.return_value = beatcloud_tracks
        mock_get_beatcloud_tracks.assert_called_once()
