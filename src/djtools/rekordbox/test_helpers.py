import inspect
import os
import re
from urllib.parse import unquote

from bs4 import BeautifulSoup
import pytest

from djtools.rekordbox.helpers import (
    BooleanNode,
    copy_file,
    get_playlist_track_locations,
    set_tag,
)

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


def test_copy_file(tmpdir, test_track):
    dest_dir = os.path.join(tmpdir, "output").replace(os.sep, "/")
    os.makedirs(dest_dir)
    old_track_loc = test_track["Location"]
    copy_file(track=test_track, destination=dest_dir)
    new_track_loc = test_track["Location"]
    loc_prefix = inspect.signature(
        copy_file
    ).parameters.get("loc_prefix").default
    new_file_path = os.path.join(
        dest_dir, os.path.basename(old_track_loc)
    ).replace(os.sep, "/")
    assert new_track_loc == f"{loc_prefix}{new_file_path}"
    assert os.path.exists(unquote(new_file_path))


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


@pytest.mark.parametrize("index", [0, 5, 9])
def test_set_tag(index, test_track):
    set_tag(test_track, index)
    assert test_track.get("TrackNumber") == index
