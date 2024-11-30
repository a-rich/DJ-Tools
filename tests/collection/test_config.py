"""Testing for the config module."""

from unittest import mock

import pytest
from jinja2 import Template
from pydantic import ValidationError

from djtools.collection.config import (
    CollectionConfig,
    PlaylistConfig,
    PlaylistConfigContent,
)

from ..test_utils import mock_exists, MockOpen


def test_collectionconfig_collection_is_unset_or_missing():
    """Test for the CollectionConfig class."""
    cfg = {"collection_playlists": True, "collection_path": "not/a/real/path"}
    with pytest.raises(
        RuntimeError,
        match="Using the collection package requires the config option "
        "collection_path to be a valid collection path",
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
    cfg = {"collection_playlists": True, "collection_path": rekordbox_xml}
    with pytest.raises(
        RuntimeError,
        match=(
            "collection_playlists.yaml must exist to use the "
            "collection_playlists feature"
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
    cfg = {"collection_playlists": True, "collection_path": rekordbox_xml}
    with pytest.raises(
        RuntimeError,
        match="collection_playlists.yaml must be a valid YAML to use the "
        "collection_playlists feature",
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
def test_collectionconfig_without_template(
    rekordbox_xml, playlist_config_content, playlist_config_obj
):
    """Test for the CollectionConfig class."""
    cfg = {"collection_playlists": True, "collection_path": rekordbox_xml}
    with mock.patch(
        "builtins.open",
        MockOpen(
            files=["collection_playlists.yaml"],
            content=playlist_config_content,
        ).open,
    ):
        config = CollectionConfig(**cfg)
    assert config.playlist_config == playlist_config_obj


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
    ).open,
)
@mock.patch("djtools.collection.config.Environment.get_template")
def test_collectionconfig_with_template(mock_get_template, rekordbox_xml):
    """Test for the CollectionConfig class."""
    new_content = ""
    mock_get_template.return_value = Template(new_content)
    cfg = {"collection_playlists": True, "collection_path": rekordbox_xml}
    config = CollectionConfig(**cfg)
    assert config.playlist_config == PlaylistConfig()


@mock.patch("djtools.collection.config.Environment.get_template")
def test_collectionconfig_with_invalid_template(
    mock_get_template, rekordbox_xml
):
    """Test for the CollectionConfig class."""
    mock_template = mock.MagicMock()
    mock_template.render.side_effect = Exception("Render failed")
    mock_get_template.return_value = mock_template

    cfg = {"collection_playlists": True, "collection_path": rekordbox_xml}
    with pytest.raises(RuntimeError):
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
