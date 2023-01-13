import os
from urllib.parse import unquote

from bs4 import BeautifulSoup
import pytest

from djtools.rekordbox.copy_playlists import copy_playlists


pytest_plugins = [
 "test_data",
]


def test_copy_playlists(tmpdir, test_config, test_xml):
    target_playlists = ["Rock", "Dubstep"]
    new_xml = os.path.join(
        os.path.dirname(test_xml), "relocated_rekordbox.xml"
    ).replace(os.sep, "/")
    test_output_dir = os.path.join(tmpdir, "output").replace(os.sep, "/")
    test_config.XML_PATH = test_xml
    test_config.COPY_PLAYLISTS = target_playlists
    test_config.COPY_PLAYLISTS_DESTINATION = test_output_dir
    copy_playlists(test_config)
    assert os.listdir(test_output_dir)
    assert os.path.exists(new_xml)
    with open(new_xml, mode="r", encoding="utf-8") as _file:
        xml = BeautifulSoup(_file.read(), "xml")
    for track in xml.find_all("TRACK"):
        if not track.get("Location"):
            continue
        assert any(x in track["Genre"] for x in target_playlists)
        assert test_output_dir in unquote(track["Location"])
        

def test_copy_playlists_invalid_playlist(tmpdir, test_config, test_xml):
    playlist = "invalid_playlist"
    test_config.XML_PATH = test_xml
    test_config.COPY_PLAYLISTS = [playlist]
    test_config.COPY_PLAYLISTS_DESTINATION = tmpdir
    with pytest.raises(LookupError, match=f"{playlist} not found"):
        copy_playlists(test_config)
