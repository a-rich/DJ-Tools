import os

from bs4 import BeautifulSoup
import pytest

from djtools.rekordbox.randomize_tracks import randomize_tracks


pytest_plugins = [
    "test_data",
]


def test_randomize_tracks(test_config, test_xml, caplog):
    caplog.set_level("INFO")
    playlists = ["Melodic Techno", "Darkpsy"]
    test_config["XML_PATH"] = test_xml
    test_config["RANDOMIZE_TRACKS_PLAYLISTS"] = playlists
    randomize_tracks(test_config)
    new_xml = os.path.join(
        os.path.dirname(test_xml), f"auto_{os.path.basename(test_xml)}"
    ).replace(os.sep, "/")
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
    

def test_randomize_tracks_no_xml_path(test_config):
    del test_config["XML_PATH"]
    with pytest.raises(
        KeyError,
        match=(
            "Using the get_genres module requires the config option XML_PATH"
        ),
    ):
        randomize_tracks(test_config)


def test_randomize_tracks_xml_path_does_not_exist(test_config):
    xml_path = "nonexistent.xml"
    test_config["XML_PATH"] = xml_path
    with pytest.raises(
        FileNotFoundError,
        match=f"{xml_path} does not exist!",
    ):
        randomize_tracks(test_config)


def test_randomize_tracks_no_randomized_playlists(
    test_config, test_xml, caplog
):
    caplog.set_level("WARNING")
    test_config["XML_PATH"] = test_xml
    test_config["RANDOMIZE_TRACKS_PLAYLISTS"] = []
    ret = randomize_tracks(test_config)
    assert not ret
    assert caplog.records[0].message == (
        "Using the randomize_tracks module requires the config option "
        "RANDOMIZE_TRACKS_PLAYLISTS"
    )


def test_randomize_tracks_missing_playlist(test_config, test_xml, caplog):
    caplog.set_level("ERROR")
    playlist = "nonexistent playlist"
    test_config["XML_PATH"] = test_xml
    test_config["RANDOMIZE_TRACKS_PLAYLISTS"] = [playlist]
    randomize_tracks(test_config)
    assert caplog.records[0].message == (
        f"{playlist} not found"
    )
