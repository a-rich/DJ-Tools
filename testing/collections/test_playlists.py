"""Testing for the playlists module."""
import pytest

from djtools.collections.playlists import Playlist, RekordboxPlaylist
from djtools.collections.tracks import RekordboxTrack


@pytest.mark.parametrize(
    "playlist_name,expected_length,is_folder",
    [("My Tags", 1, True), ("Dark", 0, False)],
)
def test_rekordboxplaylist(xml, playlist_name, expected_length, is_folder):
    """Test RekordboxPlaylist class."""
    test_playlist = xml.find("NODE", {"Name": playlist_name})
    playlist = RekordboxPlaylist(test_playlist, {})
    _ = repr(playlist)
    assert len(playlist) == expected_length
    assert playlist.is_folder() == is_folder
    assert str(test_playlist) == str(playlist)
    assert test_playlist == playlist.serialize()
    try:
        RekordboxPlaylist.validate(test_playlist, playlist)
    except AssertionError:
        assert False, "RekordboxPlaylist validation failed!"


def test_rekordboxplaylist_getitem(xml):
    """Test RekordboxPlaylist class."""
    test_playlist = xml.find("NODE", {"Name": "My Tags"})
    playlist = RekordboxPlaylist(test_playlist, {})
    try:
        _ = playlist[0]
    except KeyError:
        assert False, "RekordboxPlaylist.__getitem__ failed!"


def test_rekordboxplaylist_get_playlists(xml):
    """Test RekordboxPlaylist class."""
    test_playlist = xml.find("NODE", {"Name": "My Tags"})
    playlist = RekordboxPlaylist(test_playlist, {})
    dark_playlist = playlist.get_playlists("Dark")[0]
    assert dark_playlist.get_name() == "Dark"


def test_rekordboxplaylist_get_playlists_non_folder(xml):
    """Test RekordboxPlaylist class."""
    test_playlist = xml.find("NODE", {"Name": "Hip Hop"})
    playlist = RekordboxPlaylist(test_playlist, {"2": None})
    with pytest.raises(
        RuntimeError,
        match=(
            f'Playlist "{playlist.get_name()}" is not a folder so you cannot '
            f"call get_playlists on it."
        ),
    ):
        playlist.get_playlists()


def test_rekordboxplaylist_get_playlists_root(xml):
    """Test RekordboxPlaylist class."""
    test_playlist = xml.find("NODE", {"Name": "ROOT"})
    playlist = RekordboxPlaylist(test_playlist, {"2": None})
    root_playlist = playlist.get_playlists()
    assert len(root_playlist) == 2


def test_rekordboxplaylist_get_tracks(xml):
    """Test RekordboxPlaylist class."""
    test_playlist = xml.find("NODE", {"Name": "Dark"})
    test_track = xml.find("TRACK", {"TrackID": "2"})
    test_tracks = {test_track["TrackID"]: RekordboxTrack(test_track)}
    playlist = RekordboxPlaylist(test_playlist, test_tracks)
    assert playlist.get_tracks() == {}


def test_rekordboxplaylist_raises_runtimeerror_when_appending_to_non_folder(xml):
    """Test RekordboxPlaylist class."""
    test_playlist = xml.find("NODE", {"Name": "Dark"})
    playlist = RekordboxPlaylist(test_playlist, {})
    with pytest.raises(
        RuntimeError,
        match="You can't append to a non-folder Playlist",
    ):
        playlist.add_playlist("")


def test_rekordboxplaylist_raises_runtimeerror_when_removing_folder(xml):
    """Test RekordboxPlaylist class."""
    playlist = RekordboxPlaylist(xml.find("NODE", {"Name": "Dark"}))
    with pytest.raises(
        RuntimeError,
        match="Can't remove playlist from a non-folder playlist.",
    ):
        playlist.remove_playlist("")


def test_rekordboxplaylist_newplaylist_raises_runtimeerror_with_both_playlists_and_tracks():
    """Test RekordboxPlaylist class."""
    with pytest.raises(
        RuntimeError,
        match=(
            "You must not provide both a list of RekordboxPlaylists and a "
            "list of RekordboxTracks"
        ),
    ):
        RekordboxPlaylist.new_playlist("", playlists=[], tracks={})


def test_rekordboxplaylist_newplaylist_raises_runtimeerror_with_no_playlists_or_tracks():
    """Test RekordboxPlaylist class."""
    with pytest.raises(
        RuntimeError,
        match=(
            "You must provide either a list of RekordboxPlaylists or a "
            "list of RekordboxTracks"
        ),
    ):
        RekordboxPlaylist.new_playlist("", playlists=None, tracks=None)


def test_rekordboxplaylist_raises_type_error():
    """Test Playlist class."""
    with pytest.raises(
        TypeError,
        match=(
            "Can't instantiate abstract class Playlist with abstract method"
        ),
    ):
        Playlist()
