"""Testing for the playlist_builder module."""

from unittest import mock

import pytest

from djtools.collection.config import (
    PlaylistConfig,
    PlaylistConfigContent,
    PlaylistRemainder,
)
from djtools.collection.playlist_builder import (
    collection_playlists,
    PLAYLIST_NAME,
)
from djtools.collection.rekordbox_collection import RekordboxCollection
from djtools.collection.rekordbox_playlist import RekordboxPlaylist


@pytest.mark.parametrize(
    "remainder_type",
    [PlaylistRemainder.FOLDER, PlaylistRemainder.PLAYLIST],
)
def test_collection_playlists_makes_unused_tags_playlists(
    remainder_type,
    config,
    rekordbox_collection,
    rekordbox_xml,
    playlist_config_obj,
):
    """Test for the collection_playlists function."""
    config.collection.collection_path = rekordbox_xml
    config.collection.collection_playlists_remainder = remainder_type
    new_path = rekordbox_xml.parent / "test_collection"

    tags = {
        tag
        for value in rekordbox_collection.get_all_tags().values()
        for tag in value
    }
    some_tag = next(iter(tags))
    tags.remove(some_tag)

    playlist_config_obj.combiner = None
    playlist_config_obj.tags.playlists = [some_tag]
    config.collection.playlist_config = playlist_config_obj

    collection_playlists(config, path=new_path)

    # Since our "tags" config only specifies one tag, and there is more than
    # one tag in the collection, there must be a playlist called "Unused Tags".
    collection = RekordboxCollection(new_path)
    assert collection.get_playlists("Unused Tags")
    unused_tags_playlists = collection.get_playlists("Unused Tags")[0]

    if remainder_type == PlaylistRemainder.FOLDER:
        # If collection_playlists_remainder is set to "folder", then
        # "Unused Tags" will be a folder containing one playlist for each
        # unused tag.
        assert unused_tags_playlists.is_folder()

        for playlist in unused_tags_playlists:
            tag_playlist = playlist.get_name()

            # The name of the playlist will be one of the tags in the
            # collection.
            assert tag_playlist in tags

            # The name of the playlist will be a tag that's not specified in
            # the "tags" section of the playlist config.
            assert tag_playlist != some_tag

            # Every track in that playlist will have the tag that is the name
            # of that playlist.
            assert all(
                tag_playlist in track.get_tags()
                for track in playlist.get_tracks().values()
            )
    else:
        # If collection_playlists_remainder is set to "playlist", then
        # "Unused Tags" will be a playlist containing all the tracks having at
        # least one of the unused tags.
        assert not unused_tags_playlists.is_folder()

        for track in unused_tags_playlists.get_tracks().values():
            track_tags = track.get_tags()
            for tag in track_tags:
                if tag == some_tag:
                    # If the tag that was specified in the "tags" section of
                    # the playlist config appears in this track, then it must
                    # be the case that it also has other tags which are unused.
                    assert len(track_tags) > 1
                    continue

                # Otherwise, the tag must be one of the unused tags.
                assert tag in tags


@mock.patch(
    "djtools.collection.playlist_builder.print_playlists_tag_statistics"
)
def test_collection_playlists_prints_playlist_tag_statistics(
    mock_print_playlists_tag_statistics,
    config,
    rekordbox_xml,
    playlist_config_obj,
):
    """Test for the collection_playlists function."""
    config.collection.collection_path = rekordbox_xml
    config.verbosity = 1
    config.collection.playlist_config = playlist_config_obj

    collection_playlists(config, path=rekordbox_xml.parent / "test_collection")

    assert mock_print_playlists_tag_statistics.call_count == 1


@pytest.mark.parametrize(
    "invalid_expression",
    [
        "this & & will be invalid",
        {
            "name": "invalid expression",
            "tag_content": "this & & will be invalid",
        },
    ],
)
def test_collection_playlists_handles_error_parsing_expression(
    invalid_expression, config, rekordbox_xml, playlist_config_obj, caplog
):
    """Test for the collection_playlists function."""
    caplog.set_level("WARNING")
    config.collection.collection_path = rekordbox_xml
    playlist_config_obj.tags = None
    playlist_config_obj.combiner.playlists = [
        PlaylistConfigContent(
            name="test",
            playlists=[invalid_expression],
        )
    ]
    config.collection.playlist_config = playlist_config_obj

    collection_playlists(config, path=rekordbox_xml.parent / "test_collection")

    assert caplog.records[0].message.startswith(
        "Error parsing expression: this & & will be invalid"
    )


def test_collection_playlists_removes_existing_playlist(
    config, playlist_config_obj, rekordbox_xml
):
    """Test for the collection_playlists function."""
    collection = RekordboxCollection(rekordbox_xml)

    # A playlist_builder playlist should not already exist.
    assert not collection.get_playlists(PLAYLIST_NAME)

    # Insert a playlist_builder playlist into the collection.
    new_playlists = RekordboxPlaylist.new_playlist(PLAYLIST_NAME, playlists=[])
    root = collection.get_playlists()
    root.add_playlist(new_playlists)

    # A playlist_builder playlist should now exist.
    assert collection.get_playlists(PLAYLIST_NAME)

    # Serialize the collection containing a playlist_builder playlist.
    new_path = rekordbox_xml.parent / "test_collection"
    collection.serialize(path=new_path)
    config.collection.collection_path = new_path
    config.collection.playlist_config = playlist_config_obj

    # Run the playlist_builder on this collection to test removing the existing
    # playlist_builder playlist.
    with mock.patch(
        "djtools.collection.rekordbox_collection.RekordboxCollection.add_playlist"
    ):
        collection_playlists(config, path=new_path)

    collection = RekordboxCollection(new_path)
    assert not collection.get_playlists(PLAYLIST_NAME)


def test_collection_playlists_with_empty_playlistconfig_returns_early(
    config, rekordbox_xml, caplog
):
    """Test for the collection_playlists function."""
    caplog.set_level("WARNING")
    config.collection.collection_path = rekordbox_xml
    config.collection.playlist_config = PlaylistConfig()
    collection_playlists(config, path=rekordbox_xml.parent / "test_collection")
    assert caplog.records[0].message == (
        "Not building playlists because the playlist config is empty."
    )
