import json
import os
from typing import Optional, Tuple
from unittest import mock
from urllib.parse import unquote

from bs4 import BeautifulSoup
import pytest


class MockOpen:
    builtin_open = open

    def __init__(
        self,
        _file: str,
        user_a: Optional[Tuple[str]] = None,
        user_b: Optional[Tuple[str]] = None,
    ):
        self._user_a = user_a 
        self._user_b = user_b 
        self._file = _file 

    def open(self, *args, **kwargs):
        file_name = os.path.basename(args[0])
        if file_name == self._file:
            return self._file_strategy(file_name, *args, **kwargs)
        return self.builtin_open(*args, **kwargs)
    
    def _file_strategy(self, file_name, *args, **kwargs):
        if file_name == "config.json":
            data = '{"json_valid": false,}'
        elif file_name == "registered_users.json":
            data = (
                f'{{"{self._user_a[0]}": "{self._user_a[1]}", '
                f'"{self._user_b[0]}": "{self._user_b[1]}"}}'
            )
        elif file_name == "playlist_checker.json":
            data = (
                '{"r/techno | Top weekly Posts": '
                '"5gex4eBgWH9nieoVuV8hDC"}'
            )

        return mock.mock_open(read_data=data)(*args, **kwargs)


@pytest.fixture
def test_xml(tmpdir):
    test_dir = os.path.join(tmpdir, "input").replace(os.sep, "/")
    os.makedirs(test_dir, exist_ok=True)
    with open(
        "src/test_data/rekordbox.xml", mode="r", encoding="utf-8"
    ) as _file:
        xml = BeautifulSoup(_file.read(), "xml")
    for track in xml.find_all("TRACK"):
        if not track.get("Location"):
            continue
        track_name = os.path.basename(track["Location"])
        track["Location"] = os.path.join(
            test_dir, track_name
        ).replace(os.sep, "/")
        with open(
            unquote(track["Location"]), mode="w", encoding="utf-8"
        ) as _file:
            _file.write("")
    xml_path = os.path.join(test_dir, "rekordbox.xml").replace(os.sep, "/")
    with open(
        xml_path,
        mode="wb",
        encoding=xml.original_encoding,
    ) as _file:
        _file.write(xml.prettify("utf-8"))
    
    return xml_path


@pytest.fixture
def test_track(tmpdir):
    test_dir = os.path.join(tmpdir, "input").replace(os.sep, "/")
    os.makedirs(test_dir, exist_ok=True)
    with open(
        "src/test_data/rekordbox.xml", mode="r", encoding="utf-8"
    ) as _file:
        xml = BeautifulSoup(_file.read(), "xml")
    track = xml.find_all("TRACK")[0]
    track_name = os.path.basename(track["Location"])
    track["Location"] = os.path.join(test_dir, track_name).replace(os.sep, "/")
    with open(unquote(track["Location"]), mode="w", encoding="utf-8") as _file:
        _file.write("")

    return track


@pytest.fixture
def test_config():
    with open(
        "src/djtools/configs/config.json", mode="r", encoding="utf-8"
    ) as _file:
        config = json.load(_file)

    return config
