"""Testing for the playlist_builder module."""
from unittest import mock

import pytest

from djtools.collection.helpers import PLATFORM_REGISTRY
from djtools.collection.playlist_builder import (
    collection_playlists,
    PLAYLIST_NAME,
)

from ..test_utils import MockOpen


@pytest.mark.parametrize(
    "remainder_type", ["", "folder", "playlist", "invalid"]
)
def test_collection_playlists(
    remainder_type, config, rekordbox_xml, playlist_config
):
    """Test for the collection_playlists function."""
    config.COLLECTION_PLAYLIST_FILTERS = [
        "HipHopFilter",
        "MinimalDeepTechFilter",
    ]
    config.COLLECTION_PLAYLISTS_REMAINDER = remainder_type
    config.COLLECTION_PATH = rekordbox_xml
    config.VERBOSITY = 1
    with mock.patch(
        "builtins.open",
        MockOpen(
            files=["collection_playlists.yaml"], content=f"{playlist_config}"
        ).open,
    ):
        collection_playlists(
            config, output_path=rekordbox_xml.parent / "test_collection"
        )


def test_collection_playlists_removes_existing_playlist(
    config, playlist_config, rekordbox_xml
):
    """Test for the collection_playlists function."""
    software_config = PLATFORM_REGISTRY[next(iter(PLATFORM_REGISTRY))]
    playlist_class = software_config["playlist"]
    collection_class = software_config["collection"]
    collection = collection_class(rekordbox_xml)

    # A playlist_builder playlist should not already exist.
    assert not collection.get_playlists(PLAYLIST_NAME)

    # Insert a playlist_builder playlist into the collection.
    new_playlists = playlist_class.new_playlist(PLAYLIST_NAME, playlists=[])
    root = collection.get_playlists()
    root.add_playlist(new_playlists)

    # A playlist_builder playlist should now exist.
    assert collection.get_playlists(PLAYLIST_NAME)

    # Serialize the collection containing a playlist_builder playlist.
    new_path = rekordbox_xml.parent / "test_collection_blah"
    collection.serialize(output_path=new_path)
    config.COLLECTION_PATH = new_path

    # Run the playlist_builder on this collection to test removing the existing
    # playlist_builder playlist.
    with mock.patch(
        "builtins.open",
        MockOpen(
            files=["collection_playlists.yaml"], content=f"{playlist_config}"
        ).open,
    ):
        collection_playlists(config, output_path=new_path)

    # TODO(a-rich): Mock either RekordboxPlaylist.new_playlist or RekordboxCollection.add_playlist
    # assert not collection.get_playlists(PLAYLIST_NAME)


@mock.patch(
    "builtins.open",
    MockOpen(files=["collection_playlists.yaml"], content="{}").open,
)
def test_collection_playlists_with_empty_playlistconfig_returns_early(
    config, rekordbox_xml, caplog
):
    """Test for the collection_playlists function."""
    caplog.set_level("WARNING")
    config.COLLECTION_PATH = rekordbox_xml
    collection_playlists(
        config, output_path=rekordbox_xml.parent / "test_collection"
    )
    assert caplog.records[0].message == (
        "Not building playlists because the playlist config is empty."
    )


# def test_playlistbuilder_combiner_playlist_contains_new_playlist_selector_tracks(
#     test_playlist_config, rekordbox_xml, xml
# ):
#     """Test for the playlist_builder module."""
#     # Insert test track and Combiner playlist to target it.
#     with open(test_playlist_config, mode="r", encoding="utf-8",) as _file:
#         playlist_config = yaml.load(_file, Loader=yaml.FullLoader) or {}
#     new_track = xml.new_tag("TRACK")
#     new_track_id = "-1"
#     new_track.attrs = {
#         "TrackID": new_track_id,
#         "AverageBpm": "140.00",
#         "Genre": "Dubstep",
#         "Rating": "255",
#         "Location": "file://localhost/test-track.mp3",
#         "Comments": "",
#     }
#     collection = xml.find_all("COLLECTION")[0]
#     collection.insert(0, new_track)
#     selector_playlist = "{Dubstep} & [140]"
#     playlist_config["Combiner"]["playlists"] = [selector_playlist]
#     playlist_config = {
#         k: v for k, v in playlist_config.items()
#         if k in ["GenreTagParser", "Combiner"]
#     }
#     with open(test_playlist_config, mode="w", encoding="utf-8",) as _file:
#         playlist_config = yaml.dump(playlist_config, _file)
#     with open(rekordbox_xml, mode="wb", encoding=xml.orignal_encoding) as _file:
#         _file.write(xml.prettify("utf-8"))

#     # Test pre-conditions.
#     playlist = xml.find_all("NODE", {"Name": "Hip Hop", "Type": "1"})[0]
#     for track_key in playlist.find_all("TRACK"):
#         assert track_key["Key"] != new_track_id, (
#             "Test track should not exist in Hip Hop!"
#         )
#     test_track = None
#     for track in xml.find_all("TRACK"):
#         if not track.get("Location"):
#             continue
#         if track.get("TrackID") == new_track_id:
#             test_track = track
#     assert test_track, "Test track should exist in XML!"

#     # Run the PlaylistBuilder (GenreTagParser and Combiner).
#     PlaylistBuilder(
#         rekordbox_database=rekordbox_xml,
#         playlist_config=Path(test_playlist_config),
#     )()

#     # Load XML generated by the PlaylistBuilder.
#     path = rekordbox_xml.parent
#     file_name = rekordbox_xml.name
#     with open(path / f"auto_{file_name}", mode="r", encoding="utf-8") as _file:
#         database = BeautifulSoup(_file.read(), "xml")

#     # Test that the test track was inserted into the "Dubstep" playlist.
#     test_track = None
#     playlist = database.find_all("NODE", {"Name": "Dubstep", "Type": "1"})[0]
#     for track_key in playlist.find_all("TRACK"):
#         if track_key["Key"] == new_track_id:
#             test_track = track_key
#     assert test_track, "New track was not found in the genre playlist!"

#     # Test that the test track was inserted into the Combiner playlist.
#     test_track = None
#     test_track = None
#     playlist = database.find_all(
#         "NODE", {"Name": selector_playlist, "Type": "1"}
#     )[0]
#     for track_key in playlist.find_all("TRACK"):
#         if track_key["Key"] == new_track_id:
#             test_track = track_key
#     assert test_track, "New track was not found in the Combiner playlist!"


# def test_playlistbuilder_invalid_parser(rekordbox_xml, test_playlist_config):
#     """Test for the playlist_builder module."""
#     with open(test_playlist_config, mode="r", encoding="utf-8",) as _file:
#         playlist_config = yaml.load(_file, Loader=yaml.FullLoader) or {}
#     parser_type = "nonexistent_parser"
#     playlist_config[parser_type] = {}
#     with open(test_playlist_config, mode="w", encoding="utf-8",) as _file:
#         playlist_config = yaml.dump(playlist_config, _file)
#     with pytest.raises(
#         AttributeError,
#         match=f"{parser_type} is not a valid TagParser!"
#     ):
#         PlaylistBuilder(
#             rekordbox_database=rekordbox_xml,
#             playlist_config=test_playlist_config,
#         )()


# def test_playlistbuilder_invalid_playlist(rekordbox_xml, test_playlist_config):
#     """Test for the playlist_builder module."""
#     with open(test_playlist_config, mode="r", encoding="utf-8",) as _file:
#         playlist_config = yaml.load(_file, Loader=yaml.FullLoader) or {}
#     content = [0]
#     playlist_config = {
#         "GenreTagParser": {"name": "invalid", "playlists": content}
#     }
#     with open(test_playlist_config, mode="w", encoding="utf-8",) as _file:
#         playlist_config = yaml.dump(playlist_config, _file)
#     with pytest.raises(
#         ValueError,
#         match=f"Encountered invalid input type {type(content[0])}: {content[0]}"
#     ):
#         PlaylistBuilder(
#             rekordbox_database=rekordbox_xml,
#             playlist_config=test_playlist_config,
#         )()
