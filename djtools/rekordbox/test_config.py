"""Testing for the config module."""
from unittest import mock

import pytest

from djtools.rekordbox.config import RekordboxConfig
from djtools.utils.helpers import mock_exists


def test_rekordboxconfig():
    """Test for the RekordboxConfig class."""
    cfg = {
        "BUILD_PLAYLISTS": False,
        "COPY_PLAYLISTS": [],
        "SHUFFLE_PLAYLISTS": [],
    }
    RekordboxConfig(**cfg)


@mock.patch(
    "djtools.rekordbox.config.Path.exists",
    lambda path: mock_exists(
        [
            ("rekordbox_playlists.yaml", False),
            ("rekordbox.xml", True),
        ],
        path,
    )
)
def test_rekordboxconfig_no_build_playlists_config(test_xml):
    """Test for the RekordboxConfig class."""
    cfg = {"BUILD_PLAYLISTS": True, "XML_PATH": test_xml}
    with pytest.raises(
        RuntimeError,
        match="rekordbox_playlists.yaml must be a valid YAML to use the "
            "BUILD_PLAYLISTS feature"
    ):
        RekordboxConfig(**cfg)


def test_rekordboxconfig_no_xml():
    """Test for the RekordboxConfig class."""
    cfg = {"BUILD_PLAYLISTS": True, "XML_PATH": None}
    with pytest.raises(
        RuntimeError,
        match="Using the rekordbox package requires the config option "
            "XML_PATH to be a valid rekordbox XML file",
    ):
        RekordboxConfig(**cfg)
