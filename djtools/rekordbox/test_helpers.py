import inspect
from pathlib import Path
import re
from urllib.parse import unquote

import pytest

from djtools.rekordbox.helpers import (
    BooleanNode,
    copy_file,
    get_playlist_track_locations,
    set_tag,
)


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
    dest_dir = Path(tmpdir) / "output"
    dest_dir.mkdir(parents=True, exist_ok=True)
    old_track_loc = Path(test_track["Location"])
    copy_file(track=test_track, destination=dest_dir)
    new_track_loc = unquote(test_track["Location"])
    loc_prefix = inspect.signature(
        copy_file
    ).parameters.get("loc_prefix").default
    new_file_path = dest_dir / old_track_loc.name
    # NOTE(a-rich): `Location` attributes in the XML's `TRACK` tags always
    # have unix-style paths so comparisons made with paths created in Windows
    # must be interpretted `.as_posix()`.
    assert new_track_loc == f"{loc_prefix}{new_file_path.as_posix()}"
    assert new_file_path.exists()


def test_get_playlist_track_locations(xml):
    playlist = "Hip Hop"
    seen_tracks = set()
    ret = get_playlist_track_locations(xml, playlist, seen_tracks)
    assert seen_tracks
    assert ret
    assert len(ret) == len(seen_tracks)


def test_get_playlist_track_locations_no_playlist(xml):
    playlist = "nonexistent playlist"
    seen_tracks = set()
    with pytest.raises(LookupError, match=f"{playlist} not found"):
        get_playlist_track_locations(xml, playlist, seen_tracks)


@pytest.mark.parametrize("index", [0, 5, 9])
def test_set_tag(index, test_track):
    set_tag(test_track, index)
    assert test_track.get("TrackNumber") == index
