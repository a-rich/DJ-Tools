"""This module contains helpers for the collection package."""

from __future__ import annotations
from collections import defaultdict
from datetime import datetime
import logging
from operator import itemgetter
from pathlib import Path
import re
import shutil
from typing import Dict, List, Optional, Set, Tuple, Union

from dateutil.relativedelta import relativedelta

from djtools.collection.base_collection import Collection
from djtools.collection.base_playlist import Playlist
from djtools.collection.base_track import Track
from djtools.collection.config import (
    PlaylistConfig,
    PlaylistConfigContent,
    PlaylistName,
)
from djtools.collection.playlist_filters import PlaylistFilter
from djtools.collection.rekordbox_collection import RekordboxCollection
from djtools.collection.rekordbox_playlist import RekordboxPlaylist
from djtools.collection.rekordbox_track import RekordboxTrack
from djtools.utils.helpers import make_path


logger = logging.getLogger(__name__)
NUMERICAL_SELECTOR_REGEX = re.compile(r"(?<=\[)[^\[\]]*(?=\])")
STRING_SELECTOR_REGEX = re.compile(r"(?<={)[^{}]+:[^{}]+(?=})")
DATE_SELECTOR_REGEX = re.compile(r"(>=|>|<=|<)")
TIMEDELTA_REGEX = re.compile(
    r"^("
    r"(?P<years>[\.\d]+?)y)?"
    r"((?P<months>[\.\d]+?)m)?"
    r"((?P<weeks>[\.\d]+?)w)?"
    r"((?P<days>[\.\d]+?)d)?$"
)
INEQUALITY_MAP = {
    ">": lambda x, y: x > y,
    "<": lambda x, y: x < y,
    ">=": lambda x, y: x >= y,
    "<=": lambda x, y: x <= y,
}


# #############################################################################
# This section includes helpers for the copy_playlists module.
#   - copy_file: submitted to a ThreadPoolExecutor to copy files
# #############################################################################


@make_path
def copy_file(track: Track, destination: Path):
    """Copies a track to a destination and updates its location.

    Args:
        track: Track object.
        destination: Directory to copy tracks to.
    """
    loc = track.get_location()
    dest = destination / loc.name
    if not dest.exists():
        shutil.copyfile(loc.as_posix(), dest)
    track.set_location(dest)


# #############################################################################
# This section includes helpers for the playlist_builder module.
#   - PLATFORM_REGISTRY: used to determine which abstraction implementations to
#       use e.g. "rekordbox"
#   - build_tag_playlists: builds collection playlists using "tags" component
#       of the PlaylistConfig
#   - filter_tag_playlists: applies PlaylistFilter implementations to built tag
#       playlists
#   - aggregate_playlists: aggregates tracks from playlists in folders to
#       create an "All <folder name>" playlist in each folder
#   - add_selectors_to_tags: parses combiner playlist names and finds numerical
#       and string selectors to update the tag -> track lookup
#   - parse_numerical_selectors: used to parse numerical selectors like
#       ratings, BPMs, and years
#   - build_combiner_playlists: builds collection playlists using "combiner"
#       component of the PlaylistConfig
#   - parse_expression: evaluates the boolean algebra logic in combiner
#       playlists names to populate them with the appropriate tracks
#   - BooleanNode: used to build and evaluate the boolean algebra parse tree
#   - print_playlists_tag_statistics: prints ASCII histograms showing tag
#       frequencies in combiner playlists split by genre and other tag types
#   - scale_data: scales tag frequencies to normalize histogram height
#   - print_data: formats the string representing ASCII histograms
# #############################################################################


# As support for various platforms (Serato, Denon, Traktor, etc.) is added, the
# platform name must be registered with references to their Collection,
# Playlist, and Track implementations.
PLATFORM_REGISTRY = {
    "rekordbox": {
        "collection": RekordboxCollection,
        "playlist": RekordboxPlaylist,
        "track": RekordboxTrack,
    },
}


def build_tag_playlists(
    content: Union[PlaylistConfigContent, PlaylistName, str],
    tags_tracks: Dict[str, Dict[str, Track]],
    playlist_class: Playlist,
    tag_set: Optional[Set] = None,
) -> Optional[Playlist]:
    """Recursively traverses a playlist config to generate playlists from tags.

    Args:
        content: A component of a playlist config to create a playlist for.
        tags_tracks: Dict of tags to tracks.
        playlist_class: Playlist implementation class.
        tag_set: A set of tags seen while creating playlists. This is used to
            indicate which tags should be ignored when creating the
            "Unused Tags" playlists.

    Raises:
        ValueError: The user's playlist config must not be malformed.

    Returns:
        A Playlist or None.
    """
    if not isinstance(content, (PlaylistConfigContent, PlaylistName, str)):
        raise ValueError(f"Invalid input type {type(content)}: {content}")

    # Initialize the set of tags in case the caller didn't provide one.
    tag_set = tag_set if tag_set is not None else set()

    # This is a folder so create playlists for those playlists within it.
    if isinstance(content, PlaylistConfigContent):
        # Update the set of tags seen so these are ignored in when creating the
        # "Unused Tags" playlists.
        if content.name == "_ignore":
            tag_set.update(content.playlists)
            return None

        # Create playlists for each playlist in this folder.
        playlists = [
            build_tag_playlists(item, tags_tracks, playlist_class, tag_set)
            for item in content.playlists
        ]
        playlists = [playlist for playlist in playlists if playlist]
        if not playlists:
            logger.warning(
                f'There were no playlists created from "{content.playlists}"'
            )
            return None

        return playlist_class.new_playlist(
            name=content.name, playlists=playlists
        )

    # This is not a folder so a playlist with tracks must be created.

    # If a PlaylistName is used, then the tag_content field is used to
    # determine the tag corresponding with this playlist and the name field is
    # used to name the playlist. Otherwise, the content is a string that
    # represents both the tag and the name.
    if isinstance(content, PlaylistName):
        tag_content = content.tag_content
        name = content.name or tag_content
    else:
        tag_content = name = content

    # Apply special logic for creating a "pure" playlist. "Pure" playlists are
    # those that contain tracks with a set of genre tags that all contain the
    # sub-string indicated by the suffix of the playlist name. For example,
    # "Pure Techno" will contain tracks that have genres {"Hard Techno",
    # "Melodic Techno"} but will not contain tracks that contain
    # {"Hard Techno", "Tech House"} because "Tech House" does not contain
    # "Techno" as a sub-string.
    if tag_content.startswith("Pure "):
        # Isolate the tag to create a pure playlist for.
        tag = tag_content.split("Pure ")[-1]
        tracks_with_tag = tags_tracks.get(tag)
        if not tracks_with_tag:
            logger.warning(
                f'Can\'t make a "Pure {tag}" playlist because there are no '
                "tracks with that tag."
            )
            return None

        # Filter out tracks that aren't pure.
        pure_tag_tracks = {
            track_id: track
            for track_id, track in tracks_with_tag.items()
            if all(tag.lower() in _.lower() for _ in track.get_genre_tags())
        }
        if not pure_tag_tracks:
            logger.warning(
                f'Can\'t make a "Pure {tag}" playlist because there are no '
                f"tracks that are pure {tag}."
            )
            return None

        return playlist_class.new_playlist(name=name, tracks=pure_tag_tracks)

    # Get tracks with this tag and index it so that it's not added to the
    # "Unused Tags" playlists.
    tracks_with_tag = tags_tracks.get(tag_content)
    tag_set.add(tag_content)
    if not tracks_with_tag:
        logger.warning(f'There are no tracks with the tag "{tag_content}"')
        return None

    return playlist_class.new_playlist(name=name, tracks=tracks_with_tag)


def build_combiner_playlists(
    content: Union[PlaylistConfig, PlaylistName, str],
    tags_tracks: Dict[str, Dict[str, Track]],
    playlist_class: Playlist,
) -> Optional[Playlist]:
    """Recursively traverses a playlist config to generate playlists from tags.

    Args:
        content: A component of a playlist config to create a playlist for.
        tags_tracks: Dict of tags to tracks.
        playlist_class: Playlist implementation class.

    Raises:
        ValueError: The user's playlist config must not be malformed.

    Returns:
        A Playlist or None.
    """
    if not isinstance(content, (PlaylistConfigContent, PlaylistName, str)):
        raise ValueError(f"Invalid input type {type(content)}: {content}")

    if isinstance(content, PlaylistName):
        tag_content = content.tag_content
        name = content.name or tag_content
    elif isinstance(content, str):
        tag_content = name = content

    # This is not a folder so a playlist with tracks must be created.
    if isinstance(content, (PlaylistName, str)):
        try:
            tracks = parse_expression(tag_content, tags_tracks)
        except Exception as exc:
            logger.warning(f"Error parsing expression: {tag_content}\n{exc}")
            return None
        return playlist_class.new_playlist(name=name, tracks=tracks)

    # This is a folder so create playlists for those playlists within it.
    playlists = []
    for item in content.playlists:
        playlist = build_combiner_playlists(item, tags_tracks, playlist_class)
        if playlist:
            playlists.append(playlist)
        else:
            logger.warning(
                f"There are no tracks for the Combiner playlist: {item}"
            )
    if not playlists:
        logger.warning(
            f'There were no playlists created from "{content.playlists}"'
        )

    return playlist_class.new_playlist(name=content.name, playlists=playlists)


def filter_tag_playlists(
    playlist: Playlist, playlist_filters: List[PlaylistFilter]
) -> None:
    """Applies a list of PlaylistFilter implementations to the playlist.

    If the PlaylistFilter implementations' is_filter_playlist method evaluates
    to True, then the filter_track method is applied to each track in the
    playlist. The playlist's tracks are set to remove the tracks that have been
    filtered out.

    Args:
        playlist: Playlist to potentially have its tracks filtered.
        playlist_filters: A list of PlaylistFilter implementations used to
            filter playlist tracks.
    """
    # This is a folder so filter its playlists.
    if playlist.is_folder():
        for _playlist in playlist:
            filter_tag_playlists(_playlist, playlist_filters)
        return

    # Apply each PlaylistFilter to this playlist.
    for playlist_filter in playlist_filters:
        if not playlist_filter.is_filter_playlist(playlist):
            continue
        playlist.set_tracks(
            tracks={
                track_id: track
                for track_id, track in playlist.get_tracks().items()
                if playlist_filter.filter_track(track)
            },
        )


def aggregate_playlists(
    playlist: Playlist, playlist_class: Playlist, top_level: bool = True
) -> Dict[str, Track]:
    """Recursively aggregate tracks from folders into "All" playlists.

    Args:
        playlist: Playlist which may be a folder or not.
        playlist_class: Playlist implementation class.
        top_level: Whether or not this is the original method call.

    Returns:
        Dict of tracks.
    """
    # Get tracks from the playlist if it's not a folder.
    if not playlist.is_folder():
        return playlist.get_tracks()

    # Recursively get tracks from each playlist within this folder.
    aggregate_tracks = {
        track_id: track
        for p in playlist
        for track_id, track in aggregate_playlists(
            p, playlist_class, top_level=False
        ).items()
    }

    # Create an "All" playlist in this folder if the folder contains more than
    # one playlist.
    if len(playlist) > 1 and not top_level:
        playlist.add_playlist(
            playlist_class.new_playlist(
                name=f"All {playlist.get_name()}", tracks=aggregate_tracks
            ),
            index=0,
        )

    return aggregate_tracks


def add_selectors_to_tags(
    content: Union[PlaylistConfigContent, PlaylistName, str],
    tags_tracks: Dict[str, Dict[str, Track]],
    collection: Collection,
    auto_playlists: List[Playlist],
):
    """Recursively update the track lookup with selectors.

    Args:
        content: A component of a playlist config to create a playlist for.
        tags_tracks: Dict of tags to tracks.
        collection: Collection object.
        auto_playlists: Tag playlists built in this same run.
    """
    # This is a folder so parse selectors from playlists within it.
    if isinstance(content, PlaylistConfigContent):
        for playlist in content.playlists:
            add_selectors_to_tags(
                playlist, tags_tracks, collection, auto_playlists
            )
        return

    # This is not a folder so these playlists must have their selectors parsed.
    if isinstance(content, PlaylistName):
        tag_content = content.tag_content
    else:
        tag_content = content

    numerical_value_lookup = {}
    string_selector_type_map = {
        "artist": "get_artists",
        "comment": "get_comments",
        "date": "get_date_added",
        "key": "get_key",
        "label": "get_label",
    }
    string_value_lookup = {}
    playlists = set()

    # Grab selectors from Combiner playlist name.
    parse_numerical_selectors(
        re.findall(NUMERICAL_SELECTOR_REGEX, tag_content),
        numerical_value_lookup,
    )
    parse_string_selectors(
        re.findall(STRING_SELECTOR_REGEX, tag_content),
        string_value_lookup,
        string_selector_type_map,
        playlists,
    )

    # Add keys for numerical selectors for tracks having those values.
    for value, tag in numerical_value_lookup.items():
        if tag in tags_tracks:
            continue

        for track_id, track in collection.get_tracks().items():
            values = map(
                str,
                [round(track.get_bpm()), track.get_rating(), track.get_year()],
            )
            for val in values:
                if (isinstance(value, str) and value == val) or (
                    isinstance(value, tuple) and val in value
                ):
                    tags_tracks[tag][track_id] = track

    # Add keys for string selectors for tracks having those values.
    for selector, tag in string_value_lookup.items():
        if tag in tags_tracks:
            continue

        selector_type, selector_value = selector
        for track_id, track in collection.get_tracks().items():
            value = getattr(track, string_selector_type_map[selector_type])()
            if not value:
                continue
            if selector_type == "date":
                inequality, date, date_format = selector_value
                if not inequality:
                    if value.strftime(date_format) == date.strftime(
                        date_format
                    ):
                        tags_tracks[tag][track_id] = track
                    continue
                # In order for inequalities with lower precision levels than
                # YYYY-MM-DD to work properly, the date added value for the
                # track must be converted to the lower precision string and
                # back into a datetime object.
                value = datetime.strptime(
                    value.strftime(date_format), date_format
                )
                if not inequality(value, date):
                    continue
                tags_tracks[tag][track_id] = track
                continue
            if "*" in selector_value:
                exp = re.compile(r".*".join(selector_value.lower().split("*")))
                if re.search(exp, value.lower()):
                    tags_tracks[tag][track_id] = track
                    continue
            if value.lower() == selector_value.lower():
                tags_tracks[tag][track_id] = track

    # Get playlists for the identified playlist selectors. Not only must we get
    # playlists from the collection, but we must also get playlists from the
    # auto playlists constructed in the very same run of the playlist_builder.
    # This is because the playlists being selected may include those generated
    # by the playlist_builder.
    for playlist_name in playlists:
        playlist_key = f"{{playlist:{playlist_name}}}"
        if playlist_key in tags_tracks:
            continue

        for playlist_object in [collection, *auto_playlists]:
            for playlist in playlist_object.get_playlists(playlist_name):
                if playlist.is_folder():
                    continue
                tags_tracks[playlist_key].update(playlist.get_tracks())


def parse_numerical_selectors(
    numerical_matches: List[str],
    numerical_value_lookup: Dict[Union[str, Tuple], str],
) -> Set[str]:
    """Parses a string match of one or more numerical selectors.

    Args:
        numerical_matches: List of numerical strings.
        numerical_value_lookup: Empty dict to populate with tuples or strings
            mapping numerical ranges or values to their "tag" representation.

    Returns:
        Set of numerical selector values.
    """
    numerical_values = set()
    for match in numerical_matches:
        _range = None
        # If "match" is a digit, then it's an explicit numerical value.
        if match.isdigit():
            numerical_values.add(match)
        # If "match" is two digits separated by a "-", then it's a range.
        elif len(match.split("-")) == 2 and all(
            x.isdigit() for x in match.split("-")
        ):
            _range = list(map(int, match.split("-")))
            _range = range(min(_range), max(_range) + 1)
            if not (
                all(0 <= x <= 5 for x in _range)
                or all(6 <= x <= 999 for x in _range)  # range for ratings
                or all(  # range for BPMs
                    x >= 1000 for x in _range
                )  # range for years
            ):
                logger.error(f"Bad numerical range selector: {match}")
                continue
            numerical_values.update(map(str, _range))
        else:
            logger.error(f"Malformed numerical selector: {match}")
            continue

        numerical_value_lookup[tuple(map(str, _range or [])) or match] = (
            f"[{match}]"
        )

    return numerical_values


def parse_string_selectors(
    string_matches: List[str],
    string_value_lookup: Dict[Union[str, Tuple], str],
    string_selector_type_map: Dict[str],
    playlists: Set[str],
):
    """Parses a string match of one or more string selectors.

    Args:
        string_matches: List of strings for string selectors.
        string_value_lookup: Empty dict to populate with strings mapping string
            selectors to their "tag" representation.
        string_selector_type_map: Maps a selector type to a Track method name.
        playlists: Set for storing playlist names.
    """
    date_formats = ["%Y-%m-%d", "%Y-%m", "%Y"]

    for match in string_matches:
        selector_type, selector_value = map(str.strip, match.split(":"))
        if selector_type == "playlist":
            playlists.add(selector_value)
            continue
        if not string_selector_type_map.get(selector_type):
            logger.warning(f"{selector_type} is not a supported selector!")
            continue
        if selector_type != "date":
            string_value_lookup[(selector_type, selector_value)] = (
                f"{{{match}}}"
            )
            continue

        dates, formats, inequalities = [], [], []
        skip_date_selector = False
        for part in filter(
            None, re.split(DATE_SELECTOR_REGEX, selector_value)
        ):
            date = None
            date_format = "%Y-%m-%d"

            # Note if the part is an inequality and move onto the next part.
            if re.search(DATE_SELECTOR_REGEX, part):
                inequalities.append(INEQUALITY_MAP[part])
                continue

            # The following part may be a timedelta string...
            date = parse_timedelta(part)

            # ...but if it wasn't, it's probably an ISO format date string.
            if not date:
                for date_format in date_formats:
                    try:
                        date = datetime.strptime(part, date_format)
                    except ValueError:
                        continue
                    break

            # If there's no date, then the selector wasn't formatted correctly.
            if not date:
                skip_date_selector = True
                break

            dates.append(date)
            formats.append(date_format)

        if (
            skip_date_selector
            or len(dates) != 1
            or (len(inequalities) not in [0, 1])
        ):
            logger.warning(f"Date selector {selector_value} is invalid!")
            continue

        string_value_lookup[
            (
                selector_type,
                (
                    None if not inequalities else inequalities[0],
                    dates[0],
                    formats[0],
                ),
            )
        ] = f"{{{match}}}"


def parse_timedelta(time_str) -> Optional[datetime]:
    """
    Parse a timedelta from a string and return the relative offset from now.

    Supported units of time:
      - years
      - months
      - weeks
      - days

    Some example strings:
      - 1y
      - 6m
      - 3m2w
      - 7d

    Modified from peter's answer at https://stackoverflow.com/a/51916936

    Args:
        time_str: A string identifying a duration.

    Returns:
        A datetime.datetime object.
    """
    parts = TIMEDELTA_REGEX.match(time_str)

    if not parts:
        return None

    time_params = {
        name: float(val) for name, val in parts.groupdict().items() if val
    }

    now = datetime.now()
    time_delta = relativedelta(**time_params)
    relative_time = now - time_delta

    return relative_time


def parse_expression(
    expression: str, tags_tracks: Dict[str, Dict[str, Track]]
) -> Dict[str, Track]:
    """Parses a boolean algebra expression by constructing a tree.

    Args:
        expression: String representing boolean algebra expression.
        tags_tracks: Dict of tags to tracks.

    Returns:
        Dict of track IDs and tracks.
    """
    node = BooleanNode(tags_tracks)
    tag = ""
    for char in expression:
        if char == "(":
            node = BooleanNode(tags_tracks, parent=node)
        elif node.is_operator(char):
            tag = node.add_operand(tag)
            node.add_operator(char)
        elif char == ")":
            tag = node.add_operand(tag)
            tracks = node.evaluate()
            node = node.get_parent()
            if tracks:
                node.add_operand(tracks)
        else:
            tag += char
    tag = node.add_operand(tag)

    return node.evaluate()


class BooleanNode:
    """Node that contains boolean logic for a sub-expression."""

    def __init__(
        self,
        tags_tracks: Dict[str, Dict[str, Track]],
        parent: Optional[BooleanNode] = None,
    ):
        """Constructor.

        Args:
            tags_tracks: Dict of tags to tracks.
            parent: BooleanNode of which this node is a sub-expression.
        """
        self._ops = {
            "&": set.intersection,
            "|": set.union,
            "~": set.difference,
        }
        self._parent = parent
        self._operators = []
        self._operands = []
        self._tags_tracks = tags_tracks

    def _get_tracks(self, tag: str) -> Set[str]:
        """Gets set of track IDs for the provided tag.

        If the tag contains a wildcard, denoted with "*", then the union of
        track IDs with a tag containing the provided tag as a sub-string is
        returned.

        Args:
            tag: Tag for indexing tracks.

        Returns:
            Set of track IDs for the provided tag.
        """
        if "*" in tag and not (
            re.search(NUMERICAL_SELECTOR_REGEX, tag)
            or re.search(STRING_SELECTOR_REGEX, tag)
        ):
            exp = re.compile(r".*".join(tag.split("*")) + "$")
            tracks = {}
            for key in self._tags_tracks:
                if re.match(exp, key):
                    tracks.update(self._tags_tracks[key])
            return tracks

        return self._tags_tracks.get(tag, {})

    def add_operand(self, operand: str) -> str:
        """Add operand to BooleanNode.

        Args:
            operand: Tag or track set to be evaluated.

        Returns:
            Empty string to reset tag in the parse_expression function.
        """
        if isinstance(operand, str):
            operand = operand.strip()
            if not operand:
                return ""
        self._operands.append(operand)

        return ""

    def add_operator(self, operator: str):
        """Adds a set operation to the BooleanNode.

        Args:
            operator: Character representing a set operation.
        """
        self._operators.append(self._ops[operator])

    def evaluate(self) -> Dict[str, Track]:
        """Applies operators to the operands to produce a dict of tracks.

        Raises:
            RuntimeError: The boolean expression is malformed. It must contain
                one less operator than there are operands.

        Returns:
            A dict of tracks reduced from the boolean expression.
        """
        if len(self._operators) + 1 != len(self._operands):
            operands = [
                x if isinstance(x, str) else str(len(x)) + " tracks"
                for x in self._operands
            ]
            raise RuntimeError(
                "Invalid boolean expression:\n"
                f"\toperands: {operands}\n"
                f"\toperators: {[x.__name__ for x in self._operators]}"
            )
        while self._operators:
            tracks_a = (
                self._operands.pop(0)
                if not isinstance(self._operands[0], str)
                else self._get_tracks(tag=self._operands.pop(0))
            )
            tracks_b = (
                self._operands.pop(0)
                if not isinstance(self._operands[0], str)
                else self._get_tracks(tag=self._operands.pop(0))
            )
            operator = self._operators.pop(0)
            track_ids = operator(set(tracks_a), set(tracks_b))
            tracks = {
                track_id: track
                for track_id, track in {**tracks_a, **tracks_b}.items()
                if track_id in track_ids
            }
            self._operands.insert(0, tracks)

        return next(iter(self._operands), set())

    def get_parent(self) -> BooleanNode:
        """Gets the parent of the BooleanNode.

        Returns:
            Parent BooleanNode.
        """
        return self._parent

    def is_operator(self, char: str) -> bool:
        """Checks if a character is one that represents a set operation.

        Args:
            char: Character that may represent a set operation.

        Returns:
            Whether or not the character is an operator.
        """
        return char in self._ops


def print_playlists_tag_statistics(combiner_playlists: Playlist) -> None:
    """Prints tag statistics for Combiner playlists.

    Statistics are split out by Combiner playlist and then by TagParser type.

    Args:
        combiner_playlists: Playlist object for Combiner playlists.
    """
    playlists = []
    playlist_stack = [combiner_playlists]
    while playlist_stack:
        item = playlist_stack.pop()
        if item.is_folder():
            playlist_stack.extend(item.get_playlists())
            continue
        playlists.append(item)

    for playlist in playlists:
        tracks = playlist.get_tracks()
        if tracks:
            print(f"\n{playlist.get_name()} tag statistics:")
        playlist_tags = defaultdict(int)
        genre_tags = set()
        other_tags = set()
        for track in tracks.values():
            track_all_tags = track.get_tags()
            track_genre_tags = set(track.get_genre_tags())
            other_tags.update(set(track_all_tags).difference(track_genre_tags))
            genre_tags.update(track_genre_tags)
            for tag in track_all_tags:
                playlist_tags[tag] += 1
        for tag_subset, tags in [
            ("Genre", sorted(genre_tags)),
            ("Other", sorted(other_tags)),
        ]:
            data = {tag: playlist_tags[tag] for tag in tags}
            if data:
                print(f"\n{tag_subset}:")
                print_data(data)


def scale_data(
    data: Dict[str, int], maximum: Optional[int] = 25
) -> Dict[str, int]:
    """Scales range of data values with an upper bound.

    Args:
        data: Tag names to tag counts.
        maximum: Upper bound for re-scaled data.

    Returns:
        Re-scaled dictionary of tag names and tag counts.
    """
    data_max = max(data.items(), key=itemgetter(1))[1]

    return {
        k: max(round((v / data_max) * maximum), 1) for k, v in data.items()
    }


def print_data(data: Dict[str, int]):
    """Prints an ASCII histogram of tag data.

    Args:
        data: Tag names to tag counts.
    """
    data = {k: v for k, v in data.items() if v}
    scaled_data = scale_data(data)
    row_width = 0
    width_pad = 1
    row = max(scaled_data.items(), key=itemgetter(1))[1]
    output = ""
    while row > 0:
        output += "|"
        for key in data:
            key_width = len(key)
            key_center = round(key_width / 2)
            output += f"{' ' * (width_pad + key_center)}"
            output += f"{'*' if row <= scaled_data[key] else ' '}"
            output += f"{' ' * (width_pad + key_center)}"
        if not row_width:
            row_width = len(output)
        output += "\n"
        row -= 1
    output += "-" * row_width + "\n "
    for key in data:
        output += f"{' ' * width_pad}{key}{' ' * (width_pad + 1)}"
    print(output)
