"""Testing for the copy_playlists module."""

from pathlib import Path

import pytest

from djtools.collection.copy_playlists import copy_playlists
from djtools.collection.rekordbox_collection import RekordboxCollection


def test_copy_playlists_makes_destination_folder(
    tmpdir, config, rekordbox_xml
):
    """Test for the copy_playlists function."""
    target_playlists = ["Hip Hop"]
    test_output_dir = Path(tmpdir) / "output"
    config.collection.collection_path = rekordbox_xml
    config.collection.copy_playlists = target_playlists
    config.collection.copy_playlists_destination = Path(test_output_dir)
    new_collection = tmpdir / "test_collection"
    assert not config.collection.copy_playlists_destination.exists()
    copy_playlists(config, path=new_collection)
    assert config.collection.copy_playlists_destination.exists()


def test_copy_playlists_handles_invalid_playlist(
    tmpdir, config, rekordbox_xml
):
    """Test for the copy_playlists function."""
    playlist = "invalid_playlist"
    config.collection.collection_path = rekordbox_xml
    config.collection.copy_playlists = [playlist]
    config.collection.copy_playlists_destination = Path(tmpdir)
    with pytest.raises(LookupError, match=f"{playlist} not found"):
        copy_playlists(config)


def test_copy_playlists_find_multiple_playlists_with_the_same_name(
    tmpdir, config, rekordbox_collection, rekordbox_xml
):
    """Test for the copy_playlists function."""
    target_playlist = "Dark"
    config.collection.collection_path = rekordbox_xml
    config.collection.copy_playlists = [target_playlist]
    config.collection.copy_playlists_destination = Path(tmpdir)
    new_collection = tmpdir / "test_collection"
    old_playlist_count = len(
        rekordbox_collection.get_playlists(target_playlist)
    )
    copy_playlists(config, path=new_collection)
    collection = RekordboxCollection(new_collection)
    new_playlist_count = len(collection.get_playlists(target_playlist))
    assert old_playlist_count == new_playlist_count


def test_copy_playlists_copies_files(
    tmpdir, config, rekordbox_collection, rekordbox_xml
):
    """Test for the copy_playlists function."""
    target_playlists = ["Hip Hop", "Dark"]
    test_output_dir = Path(tmpdir) / "output"
    config.collection.collection_path = rekordbox_xml
    config.collection.copy_playlists = target_playlists
    config.collection.copy_playlists_destination = test_output_dir
    new_collection = Path(tmpdir) / "test_collection"
    old_tracks = {
        track_id: track
        for target_playlist in target_playlists
        for playlist in rekordbox_collection.get_playlists(target_playlist)
        for track_id, track in playlist.get_tracks().items()
    }
    copy_playlists(config, path=new_collection)
    num_copied_tracks = len(list(test_output_dir.iterdir()))
    assert num_copied_tracks == len(old_tracks)
    collection = RekordboxCollection(new_collection)
    new_tracks = {
        track_id: track
        for target_playlist in target_playlists
        for playlist in collection.get_playlists(target_playlist)
        for track_id, track in playlist.get_tracks().items()
    }
    for track_id, track in old_tracks.items():
        old_loc = track.get_location()
        new_loc = new_tracks[track_id].get_location()
        assert old_loc != new_loc
        assert old_loc.name == new_loc.name
        assert new_loc.parent == test_output_dir


def test_copy_playlists_creates_new_collection(config, rekordbox_xml, tmpdir):
    """Test for the copy_playlists function."""
    playlist = "Hip Hop"
    config.collection.collection_path = rekordbox_xml
    config.collection.copy_playlists = [playlist]
    config.collection.copy_playlists_destination = Path(tmpdir)
    new_collection = tmpdir / "test_collection"
    assert not new_collection.exists()
    copy_playlists(config, path=new_collection)
    assert new_collection.exists()


def test_copy_playlists_creates_new_collection_with_default_path(
    config, rekordbox_xml, tmpdir
):
    """Test for the copy_playlists function."""
    playlist = "Hip Hop"
    config.collection.collection_path = rekordbox_xml
    config.collection.copy_playlists = [playlist]
    config.collection.copy_playlists_destination = Path(tmpdir)
    new_collection = (
        config.collection.copy_playlists_destination
        / f"copied_playlists_collection{rekordbox_xml.suffix}"
    )
    assert not new_collection.exists()
    copy_playlists(config)
    assert new_collection.exists()
