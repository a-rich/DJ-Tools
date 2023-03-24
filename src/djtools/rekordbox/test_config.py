from pathlib import Path
from unittest import mock

import pytest

from djtools.rekordbox.config import RekordboxConfig
from test_data import mock_exists


pytest_plugins = [
   "test_data",
]


def test_rekordboxconfig():
    cfg = {
        "COPY_PLAYLISTS": [],
        "RANDOMIZE_PLAYLISTS": [],
        "REKORDBOX_PLAYLISTS": False,
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
def test_rekordboxconfig_no_rekordbox_playlists_config(test_xml):
    cfg = {"REKORDBOX_PLAYLISTS": True, "XML_PATH": test_xml}
    with pytest.raises(
        RuntimeError,
        match="rekordbox_playlists.yaml must be a valid YAML to use the "
            "REKORDBOX_PLAYLISTS feature"
    ):
        RekordboxConfig(**cfg)


def test_rekordboxconfig_no_xml():
    cfg = {"REKORDBOX_PLAYLISTS": True, "XML_PATH": None}
    with pytest.raises(
        RuntimeError,
        match="Using the rekordbox package requires the config option "
            "XML_PATH to be a valid rekordbox XML file",
    ):
        RekordboxConfig(**cfg)
