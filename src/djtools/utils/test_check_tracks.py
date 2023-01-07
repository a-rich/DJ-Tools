from unittest import mock

import pytest

from djtools.utils.check_tracks import compare_tracks


pytest_plugins = [
    "test_data",
]


@pytest.mark.parametrize("get_spotify_tracks_flag", [True, False])
@pytest.mark.parametrize("get_local_tracks_flag", [True, False])
@pytest.mark.parametrize("beatcloud_tracks", [[], ["track - artist"]])
@pytest.mark.parametrize("download_spotify", ["", "playlist Uploads"])
@mock.patch("djtools.utils.check_tracks.get_local_tracks", return_value={})
@mock.patch(
    "djtools.utils.check_tracks.get_beatcloud_tracks",
    return_value=["aweeeezy/Bass/2022-12-21/track - artist.mp3"],
)
@mock.patch("djtools.utils.check_tracks.get_spotify_tracks", return_value={})
def test_compare_tracks(
    mock_get_spotify_tracks,
    mock_get_beatcloud_tracks,
    mock_get_local_tracks,
    get_spotify_tracks_flag,
    get_local_tracks_flag,
    beatcloud_tracks,
    download_spotify,
    test_config,
    tmpdir,
    caplog,
):
    caplog.set_level("INFO")
    spotify_playlist = "playlist"
    test_config.CHECK_TRACKS = True
    test_config.CHECK_TRACKS_SPOTIFY_PLAYLISTS = [spotify_playlist]
    test_config.CHECK_TRACKS_LOCAL_DIRS = [str(tmpdir)]
    test_config.DOWNLOAD_SPOTIFY = download_spotify
    if get_spotify_tracks_flag or download_spotify:
        mock_get_spotify_tracks.return_value = {"playlist": ["track - artist"]}
    if get_local_tracks_flag:
        mock_get_local_tracks.return_value = {str(tmpdir): ["track - artist"]}
    ret_beatcloud_tracks, beatcloud_matches = compare_tracks(
        test_config,
        beatcloud_tracks,
        download_spotify_playlist=download_spotify,
    )
    if not get_spotify_tracks_flag and not download_spotify:
        assert caplog.records.pop(0).message == (
            "There are no Spotify tracks; make sure "
            "CHECK_TRACKS_SPOTIFY_PLAYLISTS has one or more keys from "
            "spotify_playlists.yaml"
        )
    if not get_local_tracks_flag and not download_spotify:
        assert caplog.records.pop(0).message == (
            "There are no local tracks; make sure CHECK_TRACKS_LOCAL_DIRS has "
            'one or more directories containing one or more tracks'
        )
    if not beatcloud_tracks and (
        get_spotify_tracks_flag or get_local_tracks_flag
    ):
        mock_get_beatcloud_tracks.assert_called_once()
    if get_spotify_tracks_flag and not download_spotify:
        assert caplog.records.pop(0).message == (
            "\nSpotify Playlist Tracks / Beatcloud Matches: "
            f"{len(mock_get_spotify_tracks.return_value)}"
        )
        assert caplog.records.pop(0).message == f"{spotify_playlist}:"
        assert caplog.records.pop(0).message == (
            "\t100: track - artist | track - artist"
        )
    if get_local_tracks_flag and not download_spotify:
        assert caplog.records.pop(0).message == (
            "\nLocal Directory Tracks / Beatcloud Matches: "
            f"{len(mock_get_local_tracks.return_value)}"
        )
        assert caplog.records.pop(0).message == f"{str(tmpdir)}:"
        assert caplog.records.pop(0).message == (
            "\t100: track - artist | track - artist"
        )
