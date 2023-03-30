import os
import shutil
import tempfile
from typing import List, Optional, Tuple
from unittest import mock
from urllib.parse import unquote

import pytest

from djtools.configs.config import BaseConfig
from djtools.configs.helpers import filter_dict, pkg_cfg


def mock_exists(files, path):
    for file_name, exists in files:
        if file_name == path.name:
            return exists

    return True

    
class MockOpen:
    builtin_open = open

    def __init__(
        self,
        files: List[str],
        user_a: Optional[Tuple[str]] = None,
        user_b: Optional[Tuple[str]] = None,
        content: Optional[str] = "",
        write_only: Optional[bool] = False,
    ):
        self._user_a = user_a 
        self._user_b = user_b 
        self._files = files
        self._content = content
        self._write_only = write_only

    def open(self, *args, **kwargs):
        file_name = os.path.basename(args[0])
        if file_name in self._files:
            if "w" in kwargs.get("mode"):
                return tempfile.TemporaryFile(mode=kwargs["mode"])
            elif not self._write_only:
                return self._file_strategy(file_name, *args, **kwargs)
        return self.builtin_open(*args, **kwargs)
    
    def _file_strategy(self, file_name, *args, **kwargs):
        if self._content:
            data = self._content
        elif file_name == "registered_users.yaml":
            data = (
                f'{{"{self._user_a[0]}": "{self._user_a[1]}", '
                f'"{self._user_b[0]}": "{self._user_b[1]}"}}'
            )
        else:
            data = "{}"

        return mock.mock_open(read_data=data)(*args, **kwargs)


@pytest.fixture
@mock.patch("djtools.spotify.helpers.get_spotify_client")
@mock.patch(
    "builtins.open",
    MockOpen(files=["registered_users.yaml"], write_only=True).open,
)
def test_config(mock_get_spotify_client):
    configs = {pkg: cfg() for pkg, cfg in pkg_cfg.items() if pkg != "configs"}
    joined_config = BaseConfig(
        **{
            k: v for cfg in configs.values()
            for k, v in filter_dict(cfg).items()
        }
    )

    return joined_config


@pytest.fixture
def test_playlist_config(tmpdir):
    src = "src/djtools/configs/rekordbox_playlists.yaml"
    dst = os.path.join(tmpdir, os.path.basename(src))
    shutil.copyfile(src, dst)

    return dst


@pytest.fixture(scope="session")
def test_track(xml_tmpdir, xml):
    test_dir = os.path.join(xml_tmpdir, "input").replace(os.sep, "/")
    os.makedirs(test_dir, exist_ok=True)
    track = xml.find("TRACK")
    track_name = os.path.basename(track["Location"])
    track["Location"] = os.path.join(test_dir, track_name).replace(os.sep, "/")
    with open(unquote(track["Location"]), mode="w", encoding="utf-8") as _file:
        _file.write("")

    return track


@pytest.fixture(scope="session")
def test_xml(xml_tmpdir, xml):
    for track in xml.find_all("TRACK"):
        if not track.get("Location"):
            continue
        track_name = os.path.basename(track["Location"])
        track["Location"] = os.path.join(
            xml_tmpdir, track_name
        ).replace(os.sep, "/")
        with open(
            unquote(track["Location"]), mode="w", encoding="utf-8"
        ) as _file:
            _file.write("")
    xml_path = os.path.join(xml_tmpdir, "rekordbox.xml").replace(os.sep, "/")
    with open(
        xml_path,
        mode="wb",
        encoding=xml.original_encoding,
    ) as _file:
        _file.write(xml.prettify("utf-8"))
    
    return xml_path
