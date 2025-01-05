"""Testing for the helpers module."""

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest

from djtools.collection.base_collection import Collection
from djtools.collection.base_playlist import Playlist
from djtools.collection.base_track import Track
from djtools.collection.config import (
    PlaylistConfigContent,
    PlaylistName,
    RegisteredPlatforms,
)
from djtools.collection.helpers import (
    add_selectors_to_tags,
    aggregate_playlists,
    BooleanNode,
    build_combiner_playlists,
    build_tag_playlists,
    copy_file,
    DATE_SELECTOR_REGEX,
    filter_tag_playlists,
    INEQUALITY_MAP,
    parse_expression,
    parse_numerical_selectors,
    parse_string_selectors,
    parse_timedelta,
    print_data,
    print_playlists_tag_statistics,
    scale_data,
)
from djtools.collection.platform_registry import PLATFORM_REGISTRY
from djtools.collection.rekordbox_collection import RekordboxCollection
from djtools.collection.rekordbox_playlist import RekordboxPlaylist


# pylint: disable=duplicate-code


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


def test_platform_registry_structure():
    """Test for the PLATFORM_REGISTRY object."""
    assert isinstance(PLATFORM_REGISTRY, dict)
    assert len(PLATFORM_REGISTRY) > 0
    required_class_impl_keys = {"collection", "playlist", "track"}
    required_base_class_impls = {Collection, Playlist, Track}
    for registered_software, impls in PLATFORM_REGISTRY.items():
        assert isinstance(registered_software, RegisteredPlatforms)
        assert isinstance(impls, dict)
        assert set(impls.keys()) == required_class_impl_keys
        assert (
            set(
                base
                for class_impl in impls.values()
                for base in class_impl.__bases__
            )
            == required_base_class_impls
        )


def test_build_tag_playlists_minimum_tracks_config():
    """Test the build_tag_playlists function."""
    playlist_content = PlaylistConfigContent(
        name="playlists",
        playlists=["Tag"],
    )
    playlists = build_tag_playlists(
        playlist_content,
        {"Tag": {1: None}},
        RekordboxPlaylist,
        minimum_tracks=2,
    )
    assert playlists is None


@mock.patch(
    "djtools.collection.rekordbox_track.RekordboxTrack.get_genre_tags",
    mock.Mock(return_value=["Tag"]),
)
def test_build_tag_playlists_pure_playlist_minimum_tracks_config(
    rekordbox_collection,
):
    """Test the build_tag_playlists function."""
    tracks = rekordbox_collection.get_tracks()
    example_track = tracks[list(tracks)[0]]
    playlist_content = PlaylistConfigContent(
        name="playlists",
        playlists=["Pure Tag"],
    )
    playlists = build_tag_playlists(
        playlist_content,
        {"Tag": {1: example_track}},
        RekordboxPlaylist,
        minimum_tracks=2,
    )
    assert playlists is None


def test_build_tag_playlists_raises_exception_for_invalid_input():
    """Test the build_tag_playlists function."""
    with pytest.raises(
        ValueError,
        match=re.escape(f"Invalid input type {list}: {[]}"),
    ):
        build_tag_playlists([], {}, RekordboxPlaylist)


def test_build_tag_playlists_evaluates_correctly():
    """Test the build_combiner_playlists function."""
    playlist_content = PlaylistConfigContent(
        name="playlists",
        playlists=[
            "Tag",
            PlaylistName(
                tag_content="Tag",
            ),
            PlaylistConfigContent(
                name="sub-playlists",
                playlists=[
                    "Tag",
                    PlaylistName(
                        tag_content="Tag",
                        name="Inner playlist",
                    ),
                ],
            ),
        ],
    )
    playlists = build_tag_playlists(
        playlist_content, {"Tag": {1: None}}, RekordboxPlaylist
    )
    assert len(playlists.get_playlists("Tag")) == 3
    assert len(playlists.get_playlists("Inner playlist")) == 1
    assert len(playlists.get_playlists("sub-playlists")) == 1
    assert len(playlists.get_playlists("playlists")) == 1


def test_build_tag_playlists_ignores_tags(
    rekordbox_collection, playlist_config_obj
):
    """Test the build_tag_playlists function."""
    # Aggregate all the tags from the collection and isolate one tag to
    # explicitly create a playlist for; all the remaining tags will be ignored.
    tags = {
        tag
        for value in rekordbox_collection.get_all_tags().values()
        for tag in value
    }
    some_tag = next(iter(tags))
    tags.remove(some_tag)

    # Override the playlist config so that a single folder called "Some Tag" is
    # created containing a single playlist for the tag isolated as some_tag.
    # All of the remaining tags are to be ignored.
    playlist_config_obj.tags.playlists = [
        PlaylistConfigContent(
            name="_ignore",
            playlists=list(tags),
        ),
        PlaylistConfigContent(
            name="Some Tag",
            playlists=[some_tag],
        ),
    ]

    # Create a dict of tracks keyed by their individual tags.
    tags_tracks = defaultdict(dict)
    for track_id, track in rekordbox_collection.get_tracks().items():
        for tag in track.get_tags():
            tags_tracks[tag][track_id] = track

    # Build tag playlists and get the contents of it.
    playlist = build_tag_playlists(
        playlist_config_obj.tags, tags_tracks, RekordboxPlaylist, tags
    )
    tag_playlists = playlist.get_playlists()

    # build_tag_playlists doesn't build an "Unused Tags" playlist in this case
    # because we told it to ignore every tag except for some_tag.
    assert len(tag_playlists) == 1
    assert tag_playlists[0].get_name() == "Some Tag"

    # The only playlist in our "Some Tag" folder is for the tag specified in
    # some_tag.
    assert len(tag_playlists[0]) == 1
    assert tag_playlists[0][0].get_name() == some_tag


def test_build_tag_playlists_pure_playlists(
    rekordbox_collection, playlist_config_obj
):
    """Test the build_tag_playlists function."""
    playlist_config_obj.tags.playlists = ["Techno", "Pure Techno"]

    # Create a dict of tracks keyed by their individual tags.
    tags_tracks = defaultdict(dict)
    for track_id, track in rekordbox_collection.get_tracks().items():
        for tag in track.get_tags():
            tags_tracks[tag][track_id] = track

    # Build tag playlists and get the contents of it.
    playlist = build_tag_playlists(
        playlist_config_obj.tags, tags_tracks, RekordboxPlaylist
    )

    # The "Techno" playlist will contain tracks that have a "Techno" genre tag.
    techno_playlist = playlist.get_playlists("Techno")[0]
    assert len(techno_playlist) == 2
    for track in techno_playlist.get_tracks().values():
        assert "Techno" in track.get_genre_tags()

    # The "Pure Techno" playlist will only have tracks where every genre tag
    # contains the substring "Techno" (case insensitive).
    pure_techno_playlist = playlist.get_playlists("Pure Techno")[0]
    assert len(pure_techno_playlist) == 1
    for track in pure_techno_playlist.get_tracks().values():
        for tag in track.get_genre_tags():
            assert "Techno" in tag


def test_build_tag_playlists_warnings(
    rekordbox_collection, playlist_config_obj, caplog
):
    """Test the build_tag_playlists function."""
    caplog.set_level("WARNING")

    # Create a folder that will contain no playlists.
    playlists = ["test"]
    playlist_config_obj.tags.playlists = [
        PlaylistConfigContent(
            name="Folder of non-playlists",
            playlists=playlists,
        ),
    ]

    # Create a dict of tracks keyed by their individual tags.
    tags_tracks = defaultdict(dict)
    for track_id, track in rekordbox_collection.get_tracks().items():
        for tag in track.get_tags():
            tags_tracks[tag][track_id] = track

    # Build tag playlists and get the contents of it.
    playlist = build_tag_playlists(
        playlist_config_obj.tags, tags_tracks, RekordboxPlaylist
    )

    # Since "test" doesn't exist in the collection, build_tag_playlists returns
    # None. It also warns about no tracks being found with the tag "test" and
    # warns that a folder in the configuration contains no playlists.
    assert not playlist
    assert (
        caplog.records[0].message
        == f'There are no tracks with the tag "{playlists[0]}"'
    )
    assert (
        caplog.records[1].message
        == f'There were no playlists created from "{playlists}"'
    )


def test_build_combiner_playlists_minimum_tracks_config():
    """Test the build_combiner_playlists function."""
    playlist_content = PlaylistConfigContent(
        name="playlists",
        playlists=["Tag | Tag"],
    )
    playlists = build_combiner_playlists(
        playlist_content,
        {"Tag": {1: None}},
        RekordboxPlaylist,
        minimum_tracks=2,
    )
    assert len(playlists) == 0


def test_build_combiner_playlists_raises_exception_for_invalid_input():
    """Test the build_combiner_playlists function."""
    with pytest.raises(
        ValueError,
        match=re.escape(f"Invalid input type {list}: {[]}"),
    ):
        build_combiner_playlists([], {}, RekordboxPlaylist)


@mock.patch(
    "djtools.collection.helpers.parse_expression",
    side_effect=lambda x, y: {1: None},
)
def test_build_combiner_playlists_evaluates_correctly(
    mock_parse_expression,
):
    """Test the build_combiner_playlists function."""
    expected_num_playlists = 4
    playlist_content = PlaylistConfigContent(
        name="playlists",
        playlists=[
            "Tag | Tag",
            PlaylistName(
                tag_content="Tag | Tag",
            ),
            PlaylistConfigContent(
                name="sub-playlists",
                playlists=[
                    "Tag | Tag",
                    PlaylistName(
                        tag_content="Tag | Tag",
                        name="Inner playlist",
                    ),
                ],
            ),
        ],
    )
    playlists = build_combiner_playlists(
        playlist_content, {"Tag": {1: None}}, RekordboxPlaylist
    )
    assert mock_parse_expression.call_count == expected_num_playlists
    assert len(playlists.get_playlists("Tag | Tag")) == 3
    assert len(playlists.get_playlists("Inner playlist")) == 1
    assert len(playlists.get_playlists("sub-playlists")) == 1
    assert len(playlists.get_playlists("playlists")) == 1


def test_build_combiner_playlists_warnings(caplog):
    """Test the build_combiner_playlists function."""
    caplog.set_level("WARNING")

    # A valid expression must have one more operand than there are operators.
    invalid_playlist = "Invalid ~"
    content = PlaylistConfigContent(name="test", playlists=[invalid_playlist])
    build_combiner_playlists(content, {}, RekordboxPlaylist)

    # The evaluation of a BooleanNode will error out first.
    expected_error = (
        f"Error parsing expression: {invalid_playlist}\n"
        "Invalid boolean expression:\n"
        "\toperands: ['Invalid']\n"
        "\toperators: ['difference']"
    )
    assert caplog.records[0].message == expected_error

    # When evaluation of a BooleanNode fails, the result will be None rather
    # than a Playlist.
    assert caplog.records[1].message == (
        f"There are no tracks for the Combiner playlist: {invalid_playlist}"
    )

    # If none of the expressions in a folder return a playlist, then a warning
    # will be displayed.
    assert caplog.records[2].message == (
        f'There were no playlists created from "{[invalid_playlist]}"'
    )


def test_filter_tag_playlists(rekordbox_track):
    """Test the filter_tag_playlists function."""
    # This is a nested playlist with two playlists. Both contain the same
    # single track; the one one named "Filter this" will have the track removed
    # while the other will not.
    playlist = RekordboxPlaylist.new_playlist(
        "playlists",
        playlists=[
            RekordboxPlaylist.new_playlist(
                "Folder",
                playlists=[
                    RekordboxPlaylist.new_playlist(
                        "Filter this",
                        tracks={rekordbox_track.get_id(): rekordbox_track},
                    ),
                    RekordboxPlaylist.new_playlist(
                        "Some other playlist",
                        tracks={rekordbox_track.get_id(): rekordbox_track},
                    ),
                ],
            ),
            RekordboxPlaylist.new_playlist(
                "Do not filter this",
                tracks={rekordbox_track.get_id(): rekordbox_track},
            ),
            RekordboxPlaylist.new_playlist(
                "Filter this",
                tracks={rekordbox_track.get_id(): rekordbox_track},
            ),
        ],
    )

    # This is a PlaylistFilter class that will remove tracks containing the tag
    # "Gangsta" for playlists named "Filter this".
    class TestFilter:
        "PlaylistFilter implementation."

        def filter_track(self, track: Track) -> bool:
            "Filters tracks."
            return "Gangsta" not in track.get_tags()

        def is_filter_playlist(self, playlist: Playlist) -> bool:
            "Determines if playlist should have its tracks filtered."
            return playlist.get_name() == "Filter this"

    # Apply the TestFilter.
    filter_tag_playlists(playlist, [TestFilter()])

    # Playlists named "Filter this" will have no tracks.
    filtered_playlists = playlist.get_playlists("Filter this")
    for playlist in filtered_playlists:
        assert not playlist.get_tracks()

    # Other playlists will still have tracks.
    unfiltered_playlists = playlist.get_playlists("Do Not filter this")
    for playlist in unfiltered_playlists:
        assert playlist.get_tracks()


@mock.patch(
    "djtools.collection.rekordbox_playlist.RekordboxPlaylist.aggregate",
    return_value=True,
)
def test_aggregate_playlists(rekordbox_collection):
    """Test for the aggregate_playlists function."""
    # Create a playlist for each track in the collection (one track per
    # playlist).
    tracks = rekordbox_collection.get_tracks()
    playlist = RekordboxPlaylist.new_playlist(
        "Tracks",
        playlists=[
            RekordboxPlaylist.new_playlist(
                f"Track {track.get_id()}",
                tracks={track_id: track},
            )
            for track_id, track in tracks.items()
        ],
    )

    num_playlists = len(playlist)

    # Aggregate the tracks into an "All Tracks" playlist.
    aggregate_playlists(playlist, RekordboxPlaylist)

    # aggregate_playlists will have added a new playlist.
    assert len(playlist) == num_playlists + 1

    # The added playlist will be "All" plus whatever the name of the folder is.
    all_tracks_playlist = playlist.get_playlists("All Tracks")
    assert all_tracks_playlist
    all_tracks_playlist = all_tracks_playlist[0]

    # Since the "Tracks" folder contains one track for each track in the
    # collection, the aggregated "All Tracks" playlist will contain all of
    # these tracks.
    tracks_in_playlist = all_tracks_playlist.get_tracks()
    for track_id in tracks:
        assert track_id in tracks_in_playlist


@pytest.mark.parametrize(
    "playlist_content,expected_tags,expected_tracks",
    [
        # Test only numerical selectors with existing values are added.
        (
            "[0] | [2] | [140] | [6] | [2021] | [1000]",
            ["[0]", "[140]", "[2021]"],
            [{"2", "3"}, {"1"}, {"3"}],
        ),
        # Do the same for ranges as well.
        (
            "[0-5] | [80-180] | [80-81] | [2021-2023] | [1000-1001]",
            ["[0-5]", "[80-180]", "[2021-2023]"],
            [{"1", "2", "3", "4"}, {"1", "2", "3", "4"}, {"1", "2", "3", "4"}],
        ),
        # Test only string selectors with existing values are added.
        (
            (
                "{artist:Biome} | {artist:Not there} | "
                "{comment:Whatta classic} | {comment:Not there} | "
                "{date:2021} | {date:Not there} | "
                "{key:4A} | {key:Not there} | "
                "{label:Label} | {label:Not there}"
            ),
            [
                "{artist:Biome}",
                "{comment:Whatta classic}",
                "{date:2021}",
                "{key:4A}",
                "{label:Label}",
            ],
            [{"1"}, {"2"}, {"3"}, {"4"}, {"1", "2"}],
        ),
        # Test that globbing works for string selectors.
        (
            "{artist:*Ca*} | {comment:*a*} | {key:7*} | {key:*A} | {label:*label}",
            [
                "{artist:*Ca*}",
                "{comment:*a*}",
                "{key:7*}",
                "{key:*A}",
                "{label:*label}",
            ],
            [
                {"2", "3"},
                {"1", "2", "4"},
                {"1", "2"},
                {"1", "3", "4"},
                {"1", "2", "3"},
            ],
        ),
        # Test that date added selections work as expected.
        (
            "{date:2022} | {date:>2022} | {date:>=2022} | {date:<2022} | {date:<=2022}",
            [
                "{date:2022}",
                "{date:>2022}",
                "{date:>=2022}",
                "{date:<2022}",
                "{date:<=2022}",
            ],
            [{"2"}, {"1", "4"}, {"1", "2", "4"}, {"3"}, {"2", "3"}],
        ),
        # Test that playlist selections work.
        (
            "{playlist:Hip Hop} & [0]",
            ["{playlist:Hip Hop}", "[0]"],
            [{"2"}],
        ),
        # Test that timedelta evaluate properly.
        (
            "{date:>1m}",
            ["{date:>1m}"],
            [{"1", "4"}],
        ),
    ],
)
def test_add_selectors_to_tags(
    playlist_content, expected_tags, expected_tracks, rekordbox_collection
):
    """Test for the add_selectors_to_tags function."""
    tags_tracks = defaultdict(dict)
    with mock.patch("djtools.collection.helpers.datetime") as mock_datetime:
        mock_datetime.strptime.side_effect = datetime.strptime
        mock_datetime.now.return_value = datetime(2023, 6, 25, 0, 0)
        add_selectors_to_tags(
            playlist_content, tags_tracks, rekordbox_collection, []
        )
    assert set(expected_tags) == set(tags_tracks)
    for tag, tracks in zip(expected_tags, expected_tracks):
        assert set(tags_tracks[tag]) == tracks


@pytest.mark.parametrize(
    "playlist_selector,in_tags_tracks",
    [
        ("{playlist:Genres}", False),
        ("{playlist:Hip Hop}", True),
    ],
)
def test_add_selectors_to_tags_skips_playlists_that_are_folders(
    playlist_selector, in_tags_tracks, rekordbox_collection
):
    """Test for the add_selectors_to_tags function."""
    playlist_content = f"{playlist_selector} & [0]"
    tags_tracks = defaultdict(dict)
    add_selectors_to_tags(
        playlist_content, tags_tracks, rekordbox_collection, []
    )
    assert (playlist_selector in tags_tracks) == in_tags_tracks


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
        # Numerical selectors work as follows:
        #  - value 0 through 5 represent ratings
        #  - values 6 through 999 represent BPMs
        #  - values 1000 and above represent years
        # Since this numerical selector spans 5 through 6, it tries to
        # represent both ratings and BPMs simultaneously which is invalid.
        (["5-6"], "Bad numerical range selector: 5-6"),
        # Since this numerical selector is, in fact, non-numerical, it's
        # considered malformed.
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
        "date:<2022",
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
            if re.search(DATE_SELECTOR_REGEX, key[1]):
                inequality, date = filter(
                    None, re.split(DATE_SELECTOR_REGEX, key[1])
                )
                key[1] = tuple(
                    [
                        INEQUALITY_MAP[inequality],
                        datetime.strptime(date, "%Y"),
                        "%Y",
                    ]
                )
            else:
                key[1] = tuple([None, datetime.strptime(key[1], "%Y"), "%Y"])
            key = tuple(key)
        assert key in string_lookup
        assert string_lookup[key] == f"{{{match}}}"


@pytest.mark.parametrize(
    "matches,expected",
    [
        # Valid string selectors include:
        #  - artist
        #  - comment
        #  - date
        #  - key
        #  - label
        (["bad thing:stuff"], "bad thing is not a supported selector!"),
        # Valid date formats include:
        #  -  YYYY-MM-DD
        #  -  YYYY-MM
        #  -  YYYY
        (["date:12345"], "Date selector 12345 is invalid!"),
    ],
)
def test_parse_string_selectors_warns_bad(matches, expected, caplog):
    """Test for the parse_string_selectors function."""
    caplog.set_level("WARNING")
    parse_string_selectors(matches, {}, {"date": "get_date_added"}, set())
    assert caplog.records[0].message == expected


@pytest.mark.parametrize("time_str", ["1y", "6m", "3m2w", "7d"])
def test_parse_timedelta(time_str):
    """Test for the parse_timedelta function."""
    with mock.patch("djtools.collection.helpers.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 6, 22, 0, 0)
        relative_time = parse_timedelta(time_str)
        assert relative_time < mock_datetime.now.return_value


def test_parse_expression(rekordbox_track):
    """Test for the parse_expression function."""
    track_dict = {"2": rekordbox_track}
    expression = "Hip Hop & [0]"
    tags_tracks = {"Hip Hop": track_dict, "[0]": track_dict}
    tracks = parse_expression(expression, tags_tracks)
    assert tracks == track_dict


@pytest.mark.parametrize(
    "operators,tags,expected",
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
def test_booleannode_evaluate(operators, tags, expected):
    """Test for the BooleanNode class."""
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


@pytest.mark.parametrize(
    "track_ids,operator,expected",
    [
        ([1, 1], "&", {1}),
        ([1, 2], "&", {}),
        ([1, 1], "|", {1}),
        ([1, 2], "|", {1, 2}),
        ([1, 1], "~", {}),
        ([1, 2], "~", {1}),
    ],
)
def test_booleannode_evaluates_two_sets_of_tracks_with_each_kind_of_operator(
    track_ids, operator, expected
):
    """Test for the BooleanNode class."""
    node = BooleanNode({})
    for track_id in track_ids:
        node.add_operand({track_id: None})
    node.add_operator(operator)
    result = node.evaluate().keys()
    assert (result if result else dict(result)) == expected


@pytest.mark.parametrize(
    "tag,expected",
    [
        ("Techno", {1: None}),
        ("*Techno", {1: None, 2: None}),
        ("Techno*", {1: None, 3: None}),
        ("*Techno*", {1: None, 2: None, 3: None}),
    ],
)
def test_booleannode_gets_tracks(tag, expected):
    """Test for the BooleanNode class."""
    tags_tracks = {
        "Techno": {1: None},
        "Hard Techno": {2: None},
        "Techno Stuff": {3: None},
    }
    node = BooleanNode(tags_tracks)
    assert (
        node._get_tracks(tag) == expected  # pylint: disable=protected-access
    )


def test_booleannode_raises_runtime_eror():
    """Test for the BooleanNode class.

    A valid expression must contain one more operand than there are operators.
    """
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
            genre_tags = track.get_genre_tags()
            other_tags = set(track.get_tags()).difference(set(genre_tags))
            if other_tags:
                assert "\nOther:\n" in cap.out
            if genre_tags:
                assert "\nGenre:\n" in cap.out
            call_count += int(bool(other_tags)) + int(bool(genre_tags))
    assert mock_print_data.call_count == call_count


@pytest.mark.parametrize(
    "maximum,expected",
    [
        (
            25,
            {
                "Aggro": 25,
                "Bounce": 2,
                "Chill": 1,
                "Dark": 16,
                "Melodic": 8,
                "Rave": 11,
            },
        ),
        (
            20,
            {
                "Aggro": 20,
                "Bounce": 1,
                "Chill": 1,
                "Dark": 13,
                "Melodic": 6,
                "Rave": 9,
            },
        ),
        (
            10,
            {
                "Aggro": 10,
                "Bounce": 1,
                "Chill": 1,
                "Dark": 6,
                "Melodic": 3,
                "Rave": 4,
            },
        ),
    ],
)
def test_scale_output(maximum, expected):
    """Test for the scale_output function."""
    data = {
        "Aggro": 30,
        "Bounce": 2,
        "Chill": 1,
        "Dark": 19,
        "Melodic": 9,
        "Rave": 13,
    }
    scaled_data = scale_data(data, maximum=maximum)
    assert scaled_data == expected


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
