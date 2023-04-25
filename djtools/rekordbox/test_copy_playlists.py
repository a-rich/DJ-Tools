from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup
import pytest

from djtools.rekordbox.copy_playlists import copy_playlists


def test_copy_playlists(tmpdir, test_config, test_xml):
    target_playlists = ["Hip Hop"]
    test_xml = Path(test_xml)
    new_xml = test_xml.parent / "relocated_rekordbox.xml"
    test_output_dir = Path(tmpdir) / "output"
    test_config.XML_PATH = test_xml
    test_config.COPY_PLAYLISTS = target_playlists
    test_config.COPY_PLAYLISTS_DESTINATION = Path(test_output_dir)
    copy_playlists(test_config)
    assert list(test_output_dir.iterdir())
    assert new_xml.exists()
    with open(new_xml, mode="r", encoding="utf-8") as _file:
        xml = BeautifulSoup(_file.read(), "xml")
    for track in xml.find_all("TRACK"):
        if not track.get("Location"):
            continue
        assert any(x in track["Genre"] for x in target_playlists)
        assert test_output_dir.as_posix() in unquote(track["Location"])
        

def test_copy_playlists_invalid_playlist(tmpdir, test_config, test_xml):
    playlist = "invalid_playlist"
    test_config.XML_PATH = test_xml
    test_config.COPY_PLAYLISTS = [playlist]
    test_config.COPY_PLAYLISTS_DESTINATION = Path(tmpdir)
    with pytest.raises(LookupError, match=f"{playlist} not found"):
        copy_playlists(test_config)
