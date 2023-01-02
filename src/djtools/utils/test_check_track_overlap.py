from unittest import mock

import pytest

from djtools.utils.check_track_overlap import compare_tracks


pytest_plugins = [
    "test_data",
]


@pytest.mark.parametrize("get_spotify_tracks_flag", [True, False])
@pytest.mark.parametrize("get_local_tracks_flag", [True, False])
@pytest.mark.parametrize("beatcloud_tracks", [[], ["track - artist"]])
@mock.patch("djtools.utils.check_track_overlap.get_local_tracks", return_value={})
@mock.patch(
    "djtools.utils.check_track_overlap.get_beatcloud_tracks",
    return_value=["aweeeezy/Bass/2022-12-21/track - artist.mp3"],
)
@mock.patch("djtools.utils.check_track_overlap.get_spotify_tracks", return_value={})
def test_compare_tracks(
    mock_get_spotify_tracks,
    mock_get_beatcloud_tracks,
    mock_get_local_tracks,
    get_spotify_tracks_flag,
    get_local_tracks_flag,
    beatcloud_tracks,
    test_config,
    tmpdir,
    caplog,
):
    caplog.set_level("INFO")
    playlist_name = "playlist"
    test_config["CHECK_SPOTIFY_PLAYLISTS"] = [playlist_name]
    test_config["CHECK_LOCAL_DIRS"] = [str(tmpdir)]
    if get_spotify_tracks_flag:
        mock_get_spotify_tracks.return_value = {"playlist": ["track - artist"]}
    if get_local_tracks_flag:
        mock_get_local_tracks.return_value = {str(tmpdir): ["track - artist"]}
    ret_beatcloud_tracks, beatcloud_matches = compare_tracks(
        test_config, beatcloud_tracks
    )
    if not get_spotify_tracks_flag:
        assert caplog.records.pop(0).message == (
            "There are no Spotify tracks; make sure CHECK_SPOTIFY_PLAYLISTS "
            "has one or more keys from spotify_playlists.json"
        )
    if not get_local_tracks_flag:
        assert caplog.records.pop(0).message == (
            "There are no local tracks; make sure CHECK_LOCAL_DIRS has "
            'one or more directories containing one or more tracks'
        )
    if not beatcloud_tracks and (
        get_spotify_tracks_flag or get_local_tracks_flag
    ):
        mock_get_beatcloud_tracks.assert_called_once()
    if get_spotify_tracks_flag:
        assert caplog.records.pop(0).message == (
            "\nSpotify Playlist Tracks / Beatcloud Matches: "
            f"{len(mock_get_spotify_tracks.return_value)}"
        )
        assert caplog.records.pop(0).message == f"{playlist_name}:"
        assert caplog.records.pop(0).message == (
            "\t100: track - artist | track - artist"
        )
    if get_local_tracks_flag:
        assert caplog.records.pop(0).message == (
            "\nLocal Directory Tracks / Beatcloud Matches: "
            f"{len(mock_get_local_tracks.return_value)}"
        )
        assert caplog.records.pop(0).message == f"{str(tmpdir)}:"
        assert caplog.records.pop(0).message == (
            "\t100: track - artist | track - artist"
        )
