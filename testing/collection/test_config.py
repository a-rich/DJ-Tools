"""Testing for the config module."""
from unittest import mock

import pytest
from pydantic import ValidationError

from djtools.collection.config import (
    CollectionConfig, PlaylistConfig, PlaylistConfigContent
)
from djtools.utils.helpers import mock_exists, MockOpen


def test_collectionconfig():
    """Test for the CollectionConfig class."""
    cfg = {
        "COLLECTION_PATH": "some/path",
        "COLLECTION_PLAYLISTS": False,
        "COLLECTION_PLAYLISTS_REMAINDER": "folder",
        "COPY_PLAYLISTS": [],
        "COPY_PLAYLISTS_DESTINATION": "some/path",
        "PLATFORM": "rekordbox",
        "SHUFFLE_PLAYLISTS": [],
    }
    CollectionConfig(**cfg)


@mock.patch(
    "builtins.open",
    MockOpen(
        files=["collection_playlists.yaml"],
        content="tags: invalid-content",
    ).open,
)
def test_collectionconfig_invalid_collection_playlists_config(rekordbox_xml):
    """Test for the CollectionConfig class."""
    cfg = {"COLLECTION_PLAYLISTS": True, "COLLECTION_PATH": rekordbox_xml}
    with pytest.raises(
        RuntimeError,
        match="collection_playlists.yaml must be a valid YAML to use the "
            "COLLECTION_PLAYLISTS feature"
    ):
        CollectionConfig(**cfg)


@mock.patch(
    "djtools.collection.config.Path.exists",
    lambda path: mock_exists(
        [
            ("collection_playlists.yaml", False),
            ("rekordbox.xml", True),
        ],
        path,
    )
)
def test_collectionconfig_no_collection_playlists_config(rekordbox_xml):
    """Test for the CollectionConfig class."""
    cfg = {"COLLECTION_PLAYLISTS": True, "COLLECTION_PATH": rekordbox_xml}
    with pytest.raises(
        RuntimeError,
        match="collection_playlists.yaml must be a valid YAML to use the "
            "COLLECTION_PLAYLISTS feature"
    ):
        CollectionConfig(**cfg)



def test_collectionconfig_xml_is_missing():
    """Test for the CollectionConfig class."""
    cfg = {"COLLECTION_PLAYLISTS": True, "COLLECTION_PATH": "not/a/real/path"}
    with pytest.raises(
        RuntimeError,
        match="Using the collection package requires the config option "
            "COLLECTION_PATH to be a valid collection path",
    ):
        CollectionConfig(**cfg)


def test_collectionconfig_xml_is_none():
    """Test for the CollectionConfig class."""
    cfg = {"COLLECTION_PLAYLISTS": True, "COLLECTION_PATH": None}
    with pytest.raises(
        RuntimeError,
        match="Using the collection package requires the config option "
            "COLLECTION_PATH to be a valid collection path",
    ):
        CollectionConfig(**cfg)


def test_playlistconfig(playlist_config):
    """Test for the PlaylistConfig class."""
    PlaylistConfig(**playlist_config)


def test_playlistconfig_is_invalid(playlist_config):
    """Test for the PlaylistConfig class."""
    playlist_config["invalid_key"] = {}
    with pytest.raises(ValidationError):
        PlaylistConfig(**playlist_config)


@pytest.mark.parametrize("key", ["tags", "combiner"])
def test_playlistconfigcontent(key, playlist_config):
    """Test for the PlaylistConfigContent class."""
    PlaylistConfigContent(**playlist_config[key])


@pytest.mark.parametrize("key", ["tags", "combiner"])
def test_playlistconfigcontent_is_invalid(key, playlist_config):
    """Test for the PlaylistConfigContent class."""
    content = playlist_config[key]
    content["invalid_key"] = {}
    with pytest.raises(ValidationError):
        PlaylistConfigContent(**content)
