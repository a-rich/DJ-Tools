"""Testing for the config module."""
from unittest import mock

import pytest

from djtools.collections.config import CollectionConfig
from djtools.utils.helpers import mock_exists


def test_collectionsconfig():
    """Test for the CollectionConfig class."""
    cfg = {
        "COLLECTION_PLAYLISTS": False,
        "COPY_PLAYLISTS": [],
        "SHUFFLE_PLAYLISTS": [],
    }
    CollectionConfig(**cfg)


@mock.patch(
    "djtools.collections.config.Path.exists",
    lambda path: mock_exists(
        [
            ("collection_playlists.yaml", False),
            ("rekordbox.xml", True),
        ],
        path,
    )
)
def test_collectionsconfig_no_collection_playlists_config(rekordbox_xml):
    """Test for the CollectionConfig class."""
    cfg = {"COLLECTION_PLAYLISTS": True, "COLLECTION_PATH": rekordbox_xml}
    with pytest.raises(
        RuntimeError,
        match="collection_playlists.yaml must be a valid YAML to use the "
            "COLLECTION_PLAYLISTS feature"
    ):
        CollectionConfig(**cfg)


def test_collectionsconfig_no_xml():
    """Test for the CollectionConfig class."""
    cfg = {"COLLECTION_PLAYLISTS": True, "COLLECTION_PATH": None}
    with pytest.raises(
        RuntimeError,
        match="Using the collections package requires the config option "
            "COLLECTION_PATH to be a valid collection path",
    ):
        CollectionConfig(**cfg)
