"""Testing for the playlists module."""

import pytest

from djtools.collection.rekordbox_playlist import RekordboxPlaylist


def test_rekordboxplaylist_getitem(rekordbox_playlist):
    """Test RekordboxPlaylist class."""
    try:
        _ = rekordbox_playlist[0]
    except KeyError:
        assert False, "RekordboxPlaylist.__getitem__ failed!"


@pytest.mark.parametrize("playlist,expected", [(None, 3), ("Hip Hop", 1)])
def test_rekordboxplaylist_len(playlist, expected, rekordbox_collection):
    """Test RekordboxPlaylist class."""
    # Get a playlist containing tracks (len returns number of tracks).
    if playlist:
        playlist = rekordbox_collection.get_playlists(playlist)[0]
    # Get the root playlist (len returns number of playlists at the root).
    else:
        playlist = rekordbox_collection.get_playlists()
    assert len(playlist) == expected


@pytest.mark.parametrize("index", [None, 0])
def test_rekordboxplaylist_add_playlist(index, rekordbox_playlist):
    """Test RekordboxPlaylist class."""
    test_playlist_name = "TEST"
    test_playlist = RekordboxPlaylist.new_playlist(
        test_playlist_name, tracks={}
    )
    assert not rekordbox_playlist.get_playlists(test_playlist_name)
    rekordbox_playlist.add_playlist(test_playlist, index=index)
    if index is not None:
        assert rekordbox_playlist[index] == test_playlist
    else:
        assert rekordbox_playlist[-1] == test_playlist
    rekordbox_playlist.remove_playlist(test_playlist)


def test_rekordboxplaylist_add_playlist_raises_runtimeerror_when_appending_to_non_folder(
    rekordbox_playlist,
):
    """Test RekordboxPlaylist class."""
    leaf_playlist = rekordbox_playlist.get_playlists("Dark")[0]
    with pytest.raises(
        RuntimeError,
        match="You can't append to a non-folder Playlist",
    ):
        leaf_playlist.add_playlist("")


@pytest.mark.parametrize("playlist_name", ["Hip Hop", "Dark"])
def test_rekordboxplaylist_get_name_and_get_playlists(
    playlist_name, rekordbox_playlist
):
    """Test RekordboxPlaylist class."""
    for playlist in rekordbox_playlist.get_playlists(playlist_name):
        assert playlist.get_name() == playlist_name


def test_rekordboxplaylist_get_parent(rekordbox_collection):
    """Test RekordboxPlaylist class."""
    root_playlist = rekordbox_collection.get_playlists()
    assert not root_playlist.get_parent()
    for playlist in root_playlist:
        assert playlist.get_parent() == root_playlist


def test_rekordboxplaylist_get_playlists_raises_runtimeerror_with_non_folder(
    rekordbox_playlist,
):
    """Test RekordboxPlaylist class."""
    playlist = rekordbox_playlist.get_playlists("Hip Hop")[0]
    with pytest.raises(
        RuntimeError,
        match=(
            f'Playlist "{playlist.get_name()}" is not a folder so you cannot '
            f"call get_playlists on it."
        ),
    ):
        playlist.get_playlists()


def test_rekordboxplaylist_get_playlists_with_glob(rekordbox_playlist):
    """Test RekordboxPlaylist class."""
    for playlist in rekordbox_playlist.get_playlists("Hip*", glob=True):
        assert "Hip" in playlist.get_name()


def test_rekordboxplaylist_get_tracks(rekordbox_track):
    """Test RekordboxPlaylist class."""
    tracks = {rekordbox_track.get_id(): rekordbox_track}
    playlist = RekordboxPlaylist.new_playlist("TEST", tracks=tracks)
    assert playlist.get_tracks() == tracks


@pytest.mark.parametrize(
    "playlist,expected", [("Genres", True), ("Hip Hop", False)]
)
def test_rekordboxplaylist_is_folder(playlist, expected, rekordbox_playlist):
    """Test RekordboxPlaylist class."""
    assert (
        rekordbox_playlist.get_playlists(playlist)[0].is_folder() == expected
    )


@pytest.mark.parametrize(
    "playlist_name,tracks,playlists,is_folder",
    [("TEST", {}, None, False), ("something", None, [], True)],
)
def test_rekordboxplaylist_new_playlist(
    playlist_name, tracks, playlists, is_folder
):
    """Test RekordboxPlaylist class."""
    playlist = RekordboxPlaylist.new_playlist(
        playlist_name, tracks=tracks, playlists=playlists
    )
    assert playlist.get_name() == playlist_name
    assert playlist.is_folder() == is_folder


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


def test_rekordboxplaylist_remove_playlists(rekordbox_playlist):
    """Test RekordboxPlaylist class."""
    test_playlist_name = "TEST"
    test_playlist = RekordboxPlaylist.new_playlist(
        test_playlist_name, tracks={}
    )
    rekordbox_playlist.add_playlist(test_playlist)
    assert rekordbox_playlist.get_playlists(test_playlist_name)
    rekordbox_playlist.remove_playlist(test_playlist)
    assert not rekordbox_playlist.get_playlists(test_playlist_name)


def test_rekordboxplaylist_remove_playlists_raises_runtimeerror_when_removing_folder(
    rekordbox_playlist,
):
    """Test RekordboxPlaylist class."""
    playlist = rekordbox_playlist.get_playlists("Hip Hop")[0]
    with pytest.raises(
        RuntimeError,
        match="Can't remove playlist from a non-folder playlist.",
    ):
        playlist.remove_playlist("")


def test_rekordboxplaylist_serialization(
    rekordbox_playlist_tag, rekordbox_track
):
    """Test RekordboxPlaylist class."""
    playlist = RekordboxPlaylist(
        rekordbox_playlist_tag, tracks={"2": rekordbox_track}
    )
    assert (
        repr(playlist)
        == """RekordboxPlaylist(Name="ROOT", Type="0", Count="2",
    playlists=[
        RekordboxPlaylist(Name="Genres", Type="0", Count="1",
            playlists=[
                RekordboxPlaylist(Name="Hip Hop", Type="1", Entries="1")
            ]
        ),
        RekordboxPlaylist(Name="My Tags", Type="0", Count="1",
            playlists=[
                RekordboxPlaylist(Name="Dark", Type="1", Entries="0")
            ]
        )
    ]
)"""
    )
    assert str(playlist) == str(rekordbox_playlist_tag)
    assert playlist.serialize() == rekordbox_playlist_tag


def test_rekordboxplaylist_set_parent():
    """Test RekordboxPlaylist class."""
    child_playlist = RekordboxPlaylist.new_playlist("Child", tracks={})
    parent_playlist = RekordboxPlaylist.new_playlist(
        "Parent", playlists=[child_playlist]
    )
    assert child_playlist.get_parent() is None
    child_playlist.set_parent(parent_playlist)
    assert child_playlist.get_parent() is parent_playlist


def test_rekordboxplaylist_set_tracks(rekordbox_track):
    """Test RekordboxPlaylist class."""
    old_tracks = {}
    playlist = RekordboxPlaylist.new_playlist("Test", tracks=old_tracks)
    assert playlist.get_tracks() == old_tracks
    new_tracks = {rekordbox_track.get_id(): rekordbox_track}
    playlist.set_tracks(new_tracks)
    assert playlist.get_tracks() == new_tracks
