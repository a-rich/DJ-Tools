import os
import re
from unittest import mock

from bs4 import BeautifulSoup
import pytest

from djtools.rekordbox.helpers import (
    BooleanNode, get_playlist_track_locations, rewrite_xml, set_tag, wrap_playlists
)
from test_data import MockOpen

pytest_plugins = [
    "test_data",
]


@pytest.mark.parametrize(
    "node_attributes",
    [
        (
            [set.intersection, set.union, set.difference],
            ["Jungle", "Breaks", "Techno", "Tech House"],
            {11,12},
        ),
        ([set.difference], ["*House", "Bass House"], {3,5,6,7,8}),
        ([set.intersection], ["{All DnB}", "Dark"], {2}),
    ],
)
def test_booleannode(node_attributes):
    operators, tags, expected = node_attributes
    tracks = {
        "{All DnB}": [1,2,3],
        "Acid House": [7,8],
        "Bass House": [9,10],
        "Breaks": [3,4],
        "Dark": [2,11],
        "Jungle": [1,3],
        "Tech House": [3,5,6],
        "Techno": [11,12],
    }
    for key, value in tracks.items():
        tracks[key] = {k: None for k in value}
    node = BooleanNode()
    node.operators = operators
    node.tags = tags
    result = node(tracks)
    assert result == expected


def test_booleannode_raises_runtime_eror():
    node = BooleanNode()
    node.operators = [set.union] 
    node.tags = ["tag"]
    with pytest.raises(
        RuntimeError,
        match=(
            re.escape(
                f"Invalid boolean expression: track sets: {len(node.tracks)}, "
            ) +
            re.escape(f"tags: {node.tags}, operators: ") +
            re.escape(f"{[x.__name__ for x in node.operators]}")
        ),
    ):
        node({})


def test_get_playlist_track_locations(test_xml):
    playlist = "Darkpsy"
    seen_tracks = set()
    with open(test_xml, mode="r", encoding="utf-8") as _file:
        ret = get_playlist_track_locations(
            BeautifulSoup(_file.read(), "xml"), playlist, seen_tracks
        )
    assert seen_tracks
    assert ret
    assert len(ret) == len(seen_tracks)


def test_get_playlist_track_locations_no_playlist(test_xml):
    playlist = "nonexistent playlist"
    seen_tracks = set()
    with open(test_xml, mode="r", encoding="utf-8") as _file:
        with pytest.raises(LookupError, match=f"{playlist} not found"):
            get_playlist_track_locations(
                BeautifulSoup(_file.read(), "xml"), playlist, seen_tracks
            )


@mock.patch(
    "builtins.open",
    MockOpen(
        files=["registered_users.json"],
        user_a=("aweeeezy", "/Volumes/AWEEEEZY/"),
        user_b=("other_user", "/Volumes/my_beat_stick/"),
    ).open
)
def test_rewrite_xml(test_config, test_xml):
    user_a_path= "/Volumes/AWEEEEZY/"
    user_b_path= "/Volumes/my_beat_stick/"
    test_user = "aweeeezy"
    other_user = "other_user"
    test_config["USER"] = test_user
    test_config["XML_IMPORT_USER"] = other_user
    test_config["XML_PATH"] = test_xml
    other_users_xml = os.path.join(
        os.path.dirname(test_xml), f'{other_user}_rekordbox.xml'
    ).replace(os.sep, "/")
    os.rename(test_xml, other_users_xml)

    with open(other_users_xml, mode="r", encoding="utf-8") as _file:
        soup = BeautifulSoup(_file.read(), "xml")
        for track in soup.find_all("TRACK"):
            if not track.get("Location"):
                continue
            track["Location"] = os.path.join(
                os.path.dirname(track["Location"]),
                user_b_path.strip("/"),
                os.path.basename(track["Location"]),
            ).replace(os.sep, "/")
    
    with open(
        other_users_xml, mode="wb", encoding=soup.orignal_encoding
    ) as _file:
        _file.write(soup.prettify("utf-8"))
        
    rewrite_xml(test_config)

    with open(other_users_xml, mode="r", encoding="utf-8") as _file:
        soup = BeautifulSoup(_file.read(), "xml")
        for track in soup.find_all("TRACK"):
            if not track.get("Location"):
                continue
            assert user_a_path in track["Location"]
            assert user_b_path not in track["Location"]
            example2 = track["Location"]


def test_rewrite_xml_no_xml_path(test_config):
    test_config["XML_PATH"] = ""
    with pytest.raises(
        ValueError,
        match="Using the sync_operations module's download_xml function "
            "requires the config option XML_PATH"
    ):
        rewrite_xml(test_config)


@pytest.mark.parametrize("index", [0, 5, 9])
def test_set_tag(index, test_track):
    set_tag(test_track, index)
    assert test_track.get("TrackNumber") == index


def test_wrap_playlists(test_xml, test_track):
    randomized_tracks = [test_track]
    with open(test_xml, mode="r", encoding="utf-8") as _file:
        db = BeautifulSoup(_file.read(), "xml")
    try:
        wrap_playlists(db, randomized_tracks)
        db.find_all(
            "NODE", {"Name": "AUTO_RANDOMIZE", "Type": "1"}
        )[0]
    except Exception:
        assert False
