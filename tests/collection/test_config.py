"""Testing for the config module."""

from unittest import mock

import pytest
from pydantic import ValidationError

from djtools.collection.config import (
    CollectionConfig,
    PlaylistConfig,
    PlaylistConfigContent,
)

from ..test_utils import mock_exists, MockOpen


def test_collectionconfig_collection_is_unset_or_missing():
    """Test for the CollectionConfig class."""
    cfg = {"COLLECTION_PLAYLISTS": True, "COLLECTION_PATH": "not/a/real/path"}
    with pytest.raises(
        RuntimeError,
        match="Using the collection package requires the config option "
        "COLLECTION_PATH to be a valid collection path",
    ):
        CollectionConfig(**cfg)


@mock.patch(
    "djtools.collection.config.Path.exists",
    lambda path: mock_exists(
        [
            ("collection_playlists.yaml", False),
        ],
        path,
    ),
)
def test_collectionconfig_no_collection_playlists_config(rekordbox_xml):
    """Test for the CollectionConfig class."""
    cfg = {"COLLECTION_PLAYLISTS": True, "COLLECTION_PATH": rekordbox_xml}
    with pytest.raises(
        RuntimeError,
        match=(
            "collection_playlists.yaml must exist to use the "
            "COLLECTION_PLAYLISTS feature"
        ),
    ):
        CollectionConfig(**cfg)


@mock.patch(
    "djtools.collection.config.Path.exists",
    lambda path: mock_exists(
        [
            ("collection_playlists.yaml", True),
        ],
        path,
    ),
)
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
        "COLLECTION_PLAYLISTS feature",
    ):
        CollectionConfig(**cfg)


def test_playlistconfig_example_config(playlist_config):
    """Test for the PlaylistConfig class."""
    PlaylistConfig(**playlist_config)


def test_playlistconfig_minimal_config():
    """Test for the PlaylistConfig class."""
    playlist_config = {"combiner": None, "tags": None}
    PlaylistConfig(**playlist_config)


def test_playlistconfig_is_invalid(playlist_config):
    """Test for the PlaylistConfig class."""
    playlist_config["invalid_key"] = None
    with pytest.raises(ValidationError):
        PlaylistConfig(**playlist_config)


@pytest.mark.parametrize("key", ["tags", "combiner"])
def test_playlistconfigcontent_with_example_config(key, playlist_config):
    """Test for the PlaylistConfigContent class."""
    PlaylistConfigContent(**playlist_config[key])


def test_playlistconfigcontent_with_minimal_config():
    """Test for the PlaylistConfigContent class."""
    content = {"name": "", "playlists": [{"name": "", "playlists": [""]}, ""]}
    PlaylistConfigContent(**content)


def test_playlistconfigcontent_is_invalid():
    """Test for the PlaylistConfigContent class."""
    content = {"invalid": ""}
    with pytest.raises(ValidationError):
        PlaylistConfigContent(**content)
