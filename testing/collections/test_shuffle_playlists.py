"""Testing for the shuffle_playlists module."""
from pathlib import Path

from bs4 import BeautifulSoup
import pytest

from djtools.collections.shuffle_playlists import shuffle_playlists


def test_shuffle_playlists(test_config, test_xml, caplog):
    """Test shuffle_playlists function."""
    caplog.set_level("INFO")
    playlists = ["Hip Hop"]
    test_xml = Path(test_xml)
    test_config.XML_PATH = test_xml
    test_config.SHUFFLE_PLAYLISTS = playlists
    with open(test_xml, mode="r", encoding="utf-8") as _file:
        database = BeautifulSoup(_file.read(), "xml")
    track_lookup = {
        track["TrackID"]: track for track in database.find_all("TRACK")
        if track.get("Location")
    }
    original_playlists = [
        database.find_all("NODE", {"Name": playlist, "Type": "1"})[0]
        for playlist in playlists
    ]
    original_tracks = set(
        track["Key"] for playlist in original_playlists
        for track in playlist.find_all("TRACK")
    )
    original_track_numbers = [
        track_lookup[key]["TrackNumber"] for key in original_tracks
    ]
    shuffle_playlists(test_config)
    new_xml = test_xml.parent / f"auto_{test_xml.name}"
    with open(new_xml, mode="r", encoding="utf-8") as _file:
        database = BeautifulSoup(_file.read(), "xml")
    track_lookup = {
        track["TrackID"]: track for track in database.find_all("TRACK")
        if track.get("Location")
    }
    shuffled_playlist = database.find_all(
        "NODE", {"Name": "SHUFFLE", "Type": "1"}
    )[0]
    shuffled_tracks = set(
        track["Key"] for track in shuffled_playlist.find_all("TRACK")
    )
    shuffled_track_numbers = [
        track_lookup[key]["TrackNumber"] for key in shuffled_tracks
    ]
    assert shuffled_tracks == original_tracks
    assert shuffled_track_numbers != original_track_numbers


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
