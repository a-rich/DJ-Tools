"""Testing for the check_tracks module."""
from pathlib import Path
from unittest import mock

import pytest

from djtools.utils.check_tracks import compare_tracks


@pytest.mark.parametrize("get_spotify_tracks_flag", [True, False])
@pytest.mark.parametrize("get_local_tracks_flag", [True, False])
@pytest.mark.parametrize("beatcloud_tracks", [[], [Path("track - artist")]])
@pytest.mark.parametrize("download_spotify_playlist", ["", "playlist Uploads"])
@mock.patch("djtools.utils.check_tracks.get_local_tracks", return_value={})
@mock.patch(
    "djtools.utils.check_tracks.get_beatcloud_tracks",
    return_value=[Path("aweeeezy/Bass/2022-12-21/track - artist.mp3")],
)
@mock.patch("djtools.utils.check_tracks.get_spotify_tracks", return_value={})
def test_compare_tracks(
    mock_get_spotify_tracks,
    mock_get_beatcloud_tracks,
    mock_get_local_tracks,
    get_spotify_tracks_flag,
    get_local_tracks_flag,
    beatcloud_tracks,
    download_spotify_playlist,
    config,
    tmpdir,
    caplog,
):
    """Test the compare_tracks function."""
    caplog.set_level("INFO")
    spotify_playlist = "playlist"
    tmpdir = Path(tmpdir)
    config.CHECK_TRACKS = True
    config.CHECK_TRACKS_SPOTIFY_PLAYLISTS = [spotify_playlist]
    config.LOCAL_DIRS = [tmpdir]
    config.DOWNLOAD_SPOTIFY_PLAYLIST = download_spotify_playlist
    if get_spotify_tracks_flag or download_spotify_playlist:
        mock_get_spotify_tracks.return_value = {
            "playlist": [
                {"track": {"name": "track", "artists": [{"name": "artist"}]}},
            ]
        }
    if get_local_tracks_flag:
        mock_get_local_tracks.return_value = {
            tmpdir: [Path("track - artist.mp3")]
        }
    compare_tracks(
        config,
        beatcloud_tracks,
    )
    if not get_spotify_tracks_flag and not download_spotify_playlist:
        if download_spotify_playlist:
            substring = "DOWNLOAD_SPOTIFY_PLAYLIST is a key"
        else:
            substring = "CHECK_TRACKS_SPOTIFY_PLAYLISTS has one or more keys"
        assert caplog.records.pop(0).message == (
            f"There are no Spotify tracks; make sure {substring} from "
            "spotify_playlists.yaml"
        )
    if not get_local_tracks_flag and not download_spotify_playlist:
        assert caplog.records.pop(0).message == (
            "There are no local tracks; make sure LOCAL_DIRS has "
            "one or more directories containing one or more tracks"
        )
    if not beatcloud_tracks and (
        get_spotify_tracks_flag or get_local_tracks_flag
    ):
        mock_get_beatcloud_tracks.assert_called_once()
    if get_spotify_tracks_flag and not download_spotify_playlist:
        assert caplog.records.pop(0).message == (
            "\nSpotify Playlist Tracks / Beatcloud Matches: "
            f"{len(mock_get_spotify_tracks.return_value)}"
        )
        assert caplog.records.pop(0).message == f"{spotify_playlist}:"
        assert caplog.records.pop(0).message == (
            "\t100: track - artist | track - artist"
        )
    if get_local_tracks_flag and not download_spotify_playlist:
        assert caplog.records.pop(0).message == (
            "\nLocal Directory Tracks / Beatcloud Matches: "
            f"{len(mock_get_local_tracks.return_value)}"
        )
        assert caplog.records.pop(0).message == f"{tmpdir}:"
        assert caplog.records.pop(0).message == (
            "\t100: track - artist | track - artist"
        )


@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.playlist",
    return_value={
        "tracks": {
            "items": [
                {
                    "track": {
                        "name": "title",
                        "artists": [
                            {"name": "artist"},
                        ],
                    },
                },
            ],
            "next": False,
        },
    },
)
@mock.patch("djtools.utils.helpers.get_spotify_client")
@mock.patch(
    "djtools.utils.helpers.get_playlist_ids",
    mock.Mock(return_value={"playlist": "playlist_id"}),
)
@mock.patch(
    "djtools.utils.check_tracks.get_beatcloud_tracks",
    mock.Mock(return_value=[Path("artist - title")]),
)
def test_compare_tracks_spotify_with_artist_first(
    mock_spotify, mock_spotify_playlist, config, caplog
):
    """Test the compare_tracks function."""
    caplog.set_level("INFO")
    mock_spotify.return_value.playlist.return_value = (
        mock_spotify_playlist.return_value
    )
    config.ARTIST_FIRST = True
    config.CHECK_TRACKS = True
    config.CHECK_TRACKS_SPOTIFY_PLAYLISTS = ["playlist"]
    compare_tracks(config)
    assert caplog.records[0].message == (
        'Got 1 track from Spotify playlist "playlist"'
    )
    assert caplog.records[1].message == "Got 1 track from Spotify in total"
    assert caplog.records[2].message == (
        "\nSpotify Playlist Tracks / Beatcloud Matches: 1"
    )
    assert caplog.records[3].message == "playlist:"
    assert caplog.records[4].message == (
        "\t100: artist - title | artist - title"
    )


@mock.patch(
    "djtools.utils.check_tracks.get_local_tracks",
    mock.Mock(return_value={"dir": [Path("title - artist.mp3")]}),
)
@mock.patch(
    "djtools.utils.check_tracks.get_beatcloud_tracks",
    mock.Mock(return_value=[Path("artist - title")]),
)
def test_compare_tracks_local_dirs_with_artist_first(config, caplog):
    """Test the compare_tracks function."""
    caplog.set_level("INFO")
    config.ARTIST_FIRST = True
    config.CHECK_TRACKS = True
    config.LOCAL_DIRS = ["dir"]
    compare_tracks(config)
    assert caplog.records[0].message == (
        "\nLocal Directory Tracks / Beatcloud Matches: 1"
    )
    assert caplog.records[1].message == "dir:"
    assert caplog.records[2].message == (
        "\t100: title - artist | title - artist"
    )
