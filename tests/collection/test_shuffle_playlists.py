"""Testing for the shuffle_playlists module."""

import pytest

from djtools.collection.base_playlist import Playlist
from djtools.collection.rekordbox_collection import RekordboxCollection
from djtools.collection.shuffle_playlists import shuffle_playlists


def test_shuffle_playlists_handles_missing_playlist(config, rekordbox_xml):
    """Test shuffle_playlists function."""
    playlist = "nonexistent playlist"
    config.collection.collection_path = rekordbox_xml
    config.collection.shuffle_playlists = [playlist]
    with pytest.raises(
        LookupError,
        match=f"{playlist} not found",
    ):
        shuffle_playlists(config)


def test_shuffle_playlists_shuffles_track_numbers(
    config, rekordbox_collection, rekordbox_xml, tmpdir
):
    """Test shuffle_playlists function."""
    playlist = "Hip Hop"
    config.collection.collection_path = rekordbox_xml
    config.collection.shuffle_playlists = [playlist]
    hip_hop_playlist = rekordbox_collection.get_playlists(playlist)[0]
    old_track_id_number_map = {
        track_id: track._TrackNumber  # pylint: disable=protected-access
        for track_id, track in hip_hop_playlist.get_tracks().items()
    }
    new_collection = tmpdir / "test_shuffle_collection"
    shuffle_playlists(config, path=new_collection)
    collection = RekordboxCollection(new_collection)
    hip_hop_playlist = collection.get_playlists(playlist)[0]
    new_track_id_number_map = {
        track_id: track._TrackNumber  # pylint: disable=protected-access
        for track_id, track in hip_hop_playlist.get_tracks().items()
    }
    assert old_track_id_number_map.keys() == new_track_id_number_map.keys()
    assert old_track_id_number_map.values() != new_track_id_number_map.values()


def test_shuffle_playlists_creates_new_playlist(
    config, rekordbox_collection, rekordbox_xml, tmpdir
):
    """Test shuffle_playlists function."""
    target_playlist = "Hip Hop"
    output_playlist = "SHUFFLE"
    config.collection.collection_path = rekordbox_xml
    config.collection.shuffle_playlists = [target_playlist]
    shuffle_playlist = rekordbox_collection.get_playlists(output_playlist)
    assert not shuffle_playlist
    new_collection = tmpdir / "test_collection"
    shuffle_playlists(config, path=new_collection)
    collection = RekordboxCollection(new_collection)
    shuffle_playlist = collection.get_playlists(output_playlist)[0]
    assert isinstance(shuffle_playlist, Playlist)


def test_shuffle_playlists_creates_new_collection(
    config, rekordbox_xml, tmpdir
):
    """Test shuffle_playlists function."""
    playlist = "Hip Hop"
    config.collection.collection_path = rekordbox_xml
    config.collection.shuffle_playlists = [playlist]
    new_collection = tmpdir / "test_collection"
    assert not new_collection.exists()
    shuffle_playlists(config, path=new_collection)
    assert new_collection.exists()
