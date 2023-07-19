"""Testing for the helpers module."""
from pathlib import Path
import re
from unittest import mock

import pytest

from djtools.collection.collections import RekordboxCollection
from djtools.collection.helpers import (
    BooleanNode,
    copy_file,
    # aggregate_playlists,
    build_tag_playlists,
    HipHopFilter,
    MinimalDeepTechFilter,
    parse_bpms_and_ratings,
    print_data,
    print_playlists_tag_statistics,
    scale_data,
)
from djtools.collection.tracks import RekordboxTrack


def test_aggregate_playlists():
    """Test the create_aggregate_playlists function."""


@pytest.mark.parametrize(
    "node_attributes",
    [
        (
            ["&", "|", "~"],
            ["Jungle", "Breaks", "Techno", "Tech House"],
            {11,12},
        ),
        (["~"], ["*House", "Bass House"], {3,5,6,7,8}),
        (["&"], ["{All DnB}", "Dark"], {2}),
    ],
)
def test_booleannode(node_attributes):
    """Test for the BooleanNode class."""
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
    tracks = {k: {x: None for x in v} for k, v in tracks.items()}
    node = BooleanNode(tracks)
    for operator in operators:
        node.add_operator(operator)
    for tag in tags:
        node.add_tag(tag)
    result = node.evaluate().keys()
    assert result == expected


def test_booleannode_with_multiple_expressions():
    """Test for the BooleanNode class."""
    node = BooleanNode({})
    node.add_operator("|")
    for tracks in [{2: None}, {2: None}]:
        node.add_tracks(tracks)
    result = node.evaluate().keys()
    assert result == {2}


def test_booleannode_raises_runtime_eror():
    """Test for the BooleanNode class."""
    node = BooleanNode({})
    node.add_operator("|")
    node.add_tag("tag")
    with pytest.raises(
        RuntimeError,
        match=(
            re.escape("Invalid boolean expression: track sets: 0, ") +
            re.escape("tags: ['tag'], operators: ['union']")
        ),
    ):
        node.evaluate()


def test_build_tag_playlists():
    """Test the create_playlists function."""


def test_build_tag_playlists_raises_exception_():
    """Test the create_playlists function."""
    with pytest.raises(
        ValueError,
        match=re.escape(f"Invalid input type {list}: {[]}"),
    ):
        build_tag_playlists([], {}, set())


def test_copy_file(tmpdir, rekordbox_track):
    """Test for the copy_file function."""
    dest_dir = Path(tmpdir) / "output"
    dest_dir.mkdir(parents=True, exist_ok=True)
    file_name = rekordbox_track.get_location().name
    copy_file(track=rekordbox_track, destination=dest_dir)
    new_file_path = dest_dir / file_name
    # NOTE(a-rich): `Location` attributes in the XML's `TRACK` tags always
    # have unix-style paths so comparisons made with paths created in Windows
    # must be interpreted `.as_posix()`.
    assert rekordbox_track.get_location() == new_file_path
    assert new_file_path.exists()


@pytest.mark.parametrize(
    "bass_hip_hop,genre_tags,expected",
    [
        (True, ["Hip Hop", "R&B"], False),
        (True, ["Hip Hop", "Trap"], True),
        (False, ["Hip Hop", "R&B"], True),
        (False, ["Hip Hop", "Trap"], False),
    ],
)
def test_hiphopfilter(bass_hip_hop, genre_tags, expected, rekordbox_track):
    """Test for the HipHopFilter class."""
    track_filter = HipHopFilter()
    with mock.patch.object(
        track_filter, '_bass_hip_hop', bass_hip_hop, create=True
    ), mock.patch.object(
        RekordboxTrack, "get_genre_tags", lambda x: genre_tags
    ):
        result = track_filter.filter_track(rekordbox_track)
        assert result == expected


def test_filter_tag_playlists():
    """Test the filter_tag_playlists function."""


@pytest.mark.parametrize(
    "techno,genre_tags,expected",
    [
        (True, ["Techno", "Minimal Deep Tech"], True),
        (True, ["House", "Minimal Deep Tech"], False),
        (False, ["Techno", "Minimal Deep Tech"], False),
        (False, ["House", "Minimal Deep Tech"], True),
    ],
)
def test_minimaldeeptechfilter(techno, genre_tags, expected, rekordbox_track):
    """Test for the HipHopFilter class."""
    track_filter = MinimalDeepTechFilter()
    with mock.patch.object(
        track_filter, '_techno', techno, create=True
    ), mock.patch.object(
        RekordboxTrack, "get_genre_tags", lambda x: genre_tags
    ):
        result = track_filter.filter_track(rekordbox_track)
        assert result == expected


def test_parse_bpms_and_ratings():
    """Test for the parse_bpms_and_ratings function."""
    matches = ["1", "2-3", "4,5", "140", "141-142", "143,144"]
    bpm_ratings_lookup = {}
    bpms, ratings = parse_bpms_and_ratings(matches, bpm_ratings_lookup)
    assert bpms == ["140", "141", "142", "143", "144"]
    assert ratings == ["1", "2", "3", "4", "5"]
    for match in matches:
        key = match
        if "-" in match:
            key = tuple(match.split("-"))
        elif "," in match:
            for key in match.split(","):
                assert key in bpm_ratings_lookup
                assert bpm_ratings_lookup[key] == f"[{key}]"
            continue
        assert key in bpm_ratings_lookup
        assert bpm_ratings_lookup[key] == f"[{match}]"


@pytest.mark.parametrize(
    "matches,expected",
    [
        (["5-6"], "Bad BPM or rating number range: 5-6"),
        (["bad"], "Malformed BPM or rating filter part: bad"),
    ],
)
def test_parse_bpms_and_ratings_warns_bad(matches, expected, caplog):
    """Test for the parse_bpms_and_ratings function."""
    caplog.set_level("WARNING")
    parse_bpms_and_ratings(matches, {})
    assert caplog.records[0].message == expected


def test_print_data(capsys):
    """Test for the print_data function."""
    data = {
        "Aggro": 30,
        "Bounce": 2,
        "Chill": 0,
        "Dark": 19,
        "Melodic": 9,
        "Rave": 13,
    }
    expected = (
        "|   *                                     \n" +
        "|   *                                     \n" +
        "|   *                                     \n" +
        "|   *                                     \n" +
        "|   *                                     \n" +
        "|   *                                     \n" +
        "|   *                                     \n" +
        "|   *                                     \n" +
        "|   *                                     \n" +
        "|   *               *                     \n" +
        "|   *               *                     \n" +
        "|   *               *                     \n" +
        "|   *               *                     \n" +
        "|   *               *                     \n" +
        "|   *               *                 *   \n" +
        "|   *               *                 *   \n" +
        "|   *               *                 *   \n" +
        "|   *               *        *        *   \n" +
        "|   *               *        *        *   \n" +
        "|   *               *        *        *   \n" +
        "|   *               *        *        *   \n" +
        "|   *               *        *        *   \n" +
        "|   *               *        *        *   \n" +
        "|   *       *       *        *        *   \n" +
        "|   *       *       *        *        *   \n" +
        "------------------------------------------\n" +
        "  Aggro   Bounce   Dark   Melodic   Rave  \n"
    )
    print_data(data)
    cap = capsys.readouterr()
    assert cap.out == expected


@mock.patch("djtools.collection.helpers.print_data")
def test_print_playlists_tag_statistics(
    mock_print_data, rekordbox_xml, capsys
):
    """Test for the print_playlists_tag_statistics function."""
    collection = RekordboxCollection(path=rekordbox_xml)
    playlists = collection.get_playlists("Genres")[0]
    print_playlists_tag_statistics(playlists)
    cap = capsys.readouterr()
    call_count = 0
    for playlist in playlists:
        assert f"\n{playlist.get_name()} tag statistics:" in cap.out
        for track in playlist.get_tracks().values():
            all_tags = track.get_tags()
            genre_tags = track.get_genre_tags()
            other_tags = all_tags.difference(set(genre_tags))
            if other_tags:
                assert "\nOther:\n" in cap.out
            if genre_tags:
                assert "\nGenre:\n" in cap.out
            call_count += int(bool(other_tags)) + int(bool(genre_tags))
    assert mock_print_data.call_count == call_count


def test_scale_output():
    """Test for the scale_output function."""
    data = {
        "Aggro": 30,
        "Bounce": 2,
        "Chill": 1,
        "Dark": 19,
        "Melodic": 9,
        "Rave": 13,
    }
    expected = {
        "Aggro": 25,
        "Bounce": 2,
        "Chill": 1,
        "Dark": 16,
        "Melodic": 8,
        "Rave": 11,
    }
    scaled_data = scale_data(data, maximum=25)
    assert scaled_data == expected
