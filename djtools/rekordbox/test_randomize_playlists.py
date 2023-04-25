from pathlib import Path

from bs4 import BeautifulSoup
import pytest

from djtools.rekordbox.randomize_playlists import randomize_playlists


def test_randomize_playlists(test_config, test_xml, caplog):
    caplog.set_level("INFO")
    playlists = ["Hip Hop"]
    test_xml = Path(test_xml)
    test_config.XML_PATH = test_xml
    test_config.RANDOMIZE_PLAYLISTS = playlists
    randomize_playlists(test_config)
    new_xml = test_xml.parent / f"auto_{test_xml.name}"
    with open(new_xml, mode="r", encoding="utf-8") as _file:
        db = BeautifulSoup(_file.read(), "xml")
    randomized_playlist = db.find_all(
        "NODE", {"Name": "AUTO_RANDOMIZE", "Type": "1"}
    )[0]
    original_playlists = [
        db.find_all("NODE", {"Name": playlist, "Type": "1"})[0]
        for playlist in playlists
    ]
    random_tracks = set(
        track["Key"] for track in randomized_playlist.find_all("TRACK")
    )
    original_tracks = set(
        track["Key"] for playlist in original_playlists
        for track in playlist.find_all("TRACK")
    )
    assert len(random_tracks) == len(original_tracks)
    

def test_randomize_playlists_missing_playlist(test_config, test_xml):
    playlist = "nonexistent playlist"
    test_config.XML_PATH = test_xml
    test_config.RANDOMIZE_PLAYLISTS = [playlist]
    with pytest.raises(
        LookupError,
        match=f"{playlist} not found",
    ):
        randomize_playlists(test_config)
