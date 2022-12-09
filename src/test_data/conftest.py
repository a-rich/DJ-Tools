import json
import os
from urllib.parse import unquote

from bs4 import BeautifulSoup
import pytest


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


# @pytest.fixture
# def test_rekordbox_playlists():
#     with open(
#         "src/test_data/rekordbox_playlists.json", mode="r", encoding="utf-8"
#     ) as _file:
#         config = json.load(_file)
    
#     return config


@pytest.fixture
def test_config():
    with open(
        "src/test_data/config.json", mode="r", encoding="utf-8"
    ) as _file:
        config = json.load(_file)

    return config
