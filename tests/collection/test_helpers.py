"""Testing for the helpers module."""
from datetime import datetime
from pathlib import Path
import re
from unittest import mock

import pytest

from djtools.collection.collections import Collection, RekordboxCollection
from djtools.collection.helpers import (
    BooleanNode,
    copy_file,
    # aggregate_playlists,
    build_combiner_playlists,
    build_tag_playlists,
    parse_numerical_selectors,
    parse_string_selectors,
    PLATFORM_REGISTRY,
    print_data,
    print_playlists_tag_statistics,
    scale_data,
)
from djtools.collection.playlists import Playlist


# pylint: disable=duplicate-code


def test_aggregate_playlists():
    """Test the create_aggregate_playlists function."""


@pytest.mark.parametrize(
    "node_attributes",
    [
        (
            ["&", "|", "~"],
            ["Jungle", "Breaks", "Techno", "Tech House"],
            {11, 12},
        ),
        (["~"], ["*House", "Bass House"], {3, 5, 6, 7, 8}),
        (["&"], ["{All DnB}", "Dark"], {2}),
    ],
)
def test_booleannode(node_attributes):
    """Test for the BooleanNode class."""
    operators, tags, expected = node_attributes
    tracks = {
        "{All DnB}": [1, 2, 3],
        "Acid House": [7, 8],
        "Bass House": [9, 10],
        "Breaks": [3, 4],
        "Dark": [2, 11],
        "Jungle": [1, 3],
        "Tech House": [3, 5, 6],
        "Techno": [11, 12],
    }
    tracks = {k: {x: None for x in v} for k, v in tracks.items()}
    node = BooleanNode(tracks)
    for operator in operators:
        node.add_operator(operator)
    for tag in tags:
        node.add_operand(tag)
    result = node.evaluate().keys()
    assert result == expected


def test_booleannode_with_multiple_expressions():
    """Test for the BooleanNode class."""
    node = BooleanNode({})
    node.add_operator("|")
    for tracks in [{2: None}, {2: None}]:
        node.add_operand(tracks)
    result = node.evaluate().keys()
    assert result == {2}


def test_booleannode_raises_runtime_eror():
    """Test for the BooleanNode class."""
    node = BooleanNode({})
    node.add_operator("|")
    node.add_operand("tag")
    with pytest.raises(
        RuntimeError,
        match=(
            "Invalid boolean expression:\n"
            + re.escape("\toperands: ['tag']\n")
            + re.escape("\toperators: ['union']")
        ),
    ):
        node.evaluate()


def test_build_combiner_playlists_raises_exception_():
    """Test the build_combiner_playlists function."""
    with pytest.raises(
        ValueError,
        match=re.escape(f"Invalid input type {list}: {[]}"),
    ):
        software_config = PLATFORM_REGISTRY[next(iter(PLATFORM_REGISTRY))]
        build_combiner_playlists([], {}, software_config["playlist"])


def test_build_tag_playlists_raises_exception_():
    """Test the build_tag_playlists function."""
    with pytest.raises(
        ValueError,
        match=re.escape(f"Invalid input type {list}: {[]}"),
    ):
        software_config = PLATFORM_REGISTRY[next(iter(PLATFORM_REGISTRY))]
        build_tag_playlists([], {}, software_config["playlist"])


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


def test_filter_tag_playlists():
    """Test the filter_tag_playlists function."""


def test_parse_numerical_selectors():
    """Test for the parse_numerical_selectors function."""
    matches = ["1", "2-4", "140", "141-143", "2021", "2021-2023"]
    numerical_lookup = {}
    values = parse_numerical_selectors(matches, numerical_lookup)
    assert values == {
        "1",
        "2",
        "3",
        "4",
        "140",
        "141",
        "142",
        "143",
        "2021",
        "2022",
        "2023",
    }
    for match in matches:
        key = match
        if "-" in match:
            value_range = list(map(int, match.split("-")))
            value_range[-1] += 1
            key = tuple(map(str, range(*value_range)))
        assert key in numerical_lookup
        assert numerical_lookup[key] == f"[{match}]"


@pytest.mark.parametrize(
    "matches,expected",
    [
        (["5-6"], "Bad numerical range selector: 5-6"),
        (["bad"], "Malformed numerical selector: bad"),
    ],
)
def test_parse_numerical_selectors_warns_bad(matches, expected, caplog):
    """Test for the parse_numerical_selectors function."""
    caplog.set_level("WARNING")
    parse_numerical_selectors(matches, {})
    assert caplog.records[0].message == expected


def test_parse_string_selectors():
    """Test for the parse_string_selectors function."""
    matches = [
        "artist:*Tribe*",
        "comment:*Dark*",
        "date:2022",
        # TODO(a-rich): test with key with lambda in string_lookup.
        # "date:<2022",
        "key:7A",
        "label:Some Label",
    ]
    string_lookup = {}
    type_map = {
        "artist": "get_artists",
        "comment": "get_comments",
        "date": "get_date_added",
        "key": "get_key",
        "label": "get_label",
    }
    playlists = set()
    parse_string_selectors(matches, string_lookup, type_map, playlists)
    for match in matches:
        key = tuple(map(str.strip, match.split(":")))
        if key[0] == "date":
            key = list(key)
            key[1] = tuple([None, datetime.strptime(key[1], "%Y"), "%Y"])
            key = tuple(key)
        assert key in string_lookup
        assert string_lookup[key] == f"{{{match}}}"


@pytest.mark.parametrize(
    "matches,expected",
    [
        (["bad thing:stuff"], "bad thing is not a supported selector!"),
        (["date:12345"], "Date selector 12345 is invalid!"),
    ],
)
def test_parse_string_selectors_warns_bad(matches, expected, caplog):
    """Test for the parse_string_selectors function."""
    caplog.set_level("WARNING")
    parse_string_selectors(matches, {}, {"date": "get_date_added"}, set())
    assert caplog.records[0].message == expected


def test_platform_registry():
    """Test for the PLATFORM_REGISTRY object."""
    assert isinstance(PLATFORM_REGISTRY, dict)
    assert len(PLATFORM_REGISTRY)
    for registered_software, impls in PLATFORM_REGISTRY.items():
        assert isinstance(registered_software, str)
        assert isinstance(impls, dict)
        for impl_type, impl_class in impls.items():
            assert impl_type in ["collection", "playlist"]
            assert set(impl_class.__bases__).intersection(
                set((Collection, Playlist))
            )


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
        "|   *                                     \n"
        + "|   *                                     \n"
        + "|   *                                     \n"
        + "|   *                                     \n"
        + "|   *                                     \n"
        + "|   *                                     \n"
        + "|   *                                     \n"
        + "|   *                                     \n"
        + "|   *                                     \n"
        + "|   *               *                     \n"
        + "|   *               *                     \n"
        + "|   *               *                     \n"
        + "|   *               *                     \n"
        + "|   *               *                     \n"
        + "|   *               *                 *   \n"
        + "|   *               *                 *   \n"
        + "|   *               *                 *   \n"
        + "|   *               *        *        *   \n"
        + "|   *               *        *        *   \n"
        + "|   *               *        *        *   \n"
        + "|   *               *        *        *   \n"
        + "|   *               *        *        *   \n"
        + "|   *               *        *        *   \n"
        + "|   *       *       *        *        *   \n"
        + "|   *       *       *        *        *   \n"
        + "------------------------------------------\n"
        + "  Aggro   Bounce   Dark   Melodic   Rave  \n"
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
