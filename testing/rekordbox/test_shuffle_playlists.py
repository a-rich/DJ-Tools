"""Testing for the shuffle_playlists module."""
from pathlib import Path

from bs4 import BeautifulSoup
import pytest

from djtools.rekordbox.shuffle_playlists import shuffle_playlists


def test_shuffle_playlists(test_config, test_xml, caplog):
    """Test shuffle_playlists function."""
    caplog.set_level("INFO")
    playlists = ["Hip Hop"]
    test_xml = Path(test_xml)
    test_config.XML_PATH = test_xml
    test_config.SHUFFLE_PLAYLISTS = playlists
    shuffle_playlists(test_config)
    new_xml = test_xml.parent / f"auto_{test_xml.name}"
    with open(new_xml, mode="r", encoding="utf-8") as _file:
        database = BeautifulSoup(_file.read(), "xml")
    shuffled_playlist = database.find_all(
        "NODE", {"Name": "AUTO_SHUFFLE", "Type": "1"}
    )[0]
    original_playlists = [
        database.find_all("NODE", {"Name": playlist, "Type": "1"})[0]
        for playlist in playlists
    ]
    random_tracks = set(
        track["Key"] for track in shuffled_playlist.find_all("TRACK")
    )
    original_tracks = set(
        track["Key"] for playlist in original_playlists
        for track in playlist.find_all("TRACK")
    )
    assert len(random_tracks) == len(original_tracks)


def test_shuffle_playlists_missing_playlist(test_config, test_xml):
    """Test shuffle_playlists function."""
    playlist = "nonexistent playlist"
    test_config.XML_PATH = test_xml
    test_config.SHUFFLE_PLAYLISTS = [playlist]
    with pytest.raises(
        LookupError,
        match=f"{playlist} not found",
    ):
        shuffle_playlists(test_config)
