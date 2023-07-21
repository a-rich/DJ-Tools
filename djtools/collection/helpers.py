"""This module contains helpers for the collection package."""
from __future__ import annotations
from abc import ABC, abstractmethod
from collections import defaultdict
import logging
from operator import itemgetter
from pathlib import Path
import re
import shutil
from typing import Dict, List, Optional, Set, Tuple, Union

from djtools.collection.collections import Collection, RekordboxCollection
from djtools.collection.config import PlaylistConfig, PlaylistConfigContent
from djtools.collection.playlists import Playlist, RekordboxPlaylist
from djtools.collection.tracks import Track


logger = logging.getLogger(__name__)


# #############################################################################
# This section includes helpers for the copy_playlists module.
#   - copy_file: submitted to a ThreadPoolExecutor to copy files
# #############################################################################


def copy_file(track: Track, destination: Path):
    """Copies a track to a destination and updates its location.

    Args:
        track: Track object.
        destination: Directory to copy tracks to.
    """
    loc = track.get_location()
    dest = destination / loc.name
    shutil.copyfile(loc.as_posix(), dest)
    track.set_location(dest)


# #############################################################################
# This section includes helpers for the playlist_builder module.
#   - PLATFROM_REGISTRY: used to determine which abstraction implementations to
#       use e.g. "rekordbox"
#   - build_tag_playlists: builds collection playlists using "tags" component
#       of the PlaylistConfig
#   - PlaylistFilter: abstraction for filtering Tracks from Playlists
#   - HipHopFilter: used to distinguish between actual hip hop tracks and bass
#       tracks that have hip hop influences
#   - MinimalDeepTech: used to distinguish between minimal deep tech tracks
#       with predominately house and techno influences
#   - filter_tag_playlists: applies PlaylistFilter implementations to built tag
#       playlists
#   - aggregate_playlists: aggregates tracks from playlists in folders to
#       create an "All <folder name>" playlist in each folder
#   - add_selectors_to_tags: parses combiner playlist names and finds BPM,
#       rating, and playlist selectors to update the tag -> track lookup
#   - parse_bpms_and_ratings: used to parse BPM and rating selectors
#   - build_combiner_playlists: builds collection playlists using "combiner"
#       component of the PlaylistConfig
#   - parse_expression: evaluates the boolean algebra logic in combiner
#       playlists names to populate them with the appropriate tracks
#   - BooleanNode: used to build and evaluate the boolean algebra parse tree
#   - print_playlist_tag_statistics: prints ASCII histograms showing tag
#       frequencies in combiner playlists split by genre and other tag types
#   - scale_data: scales tag frequencies to normalize histogram height
#   - print_data: formats the string representing ASCII histograms
# #############################################################################


# As support for various platforms (Serato, Denon, Traktor, etc.) is added, the
# platform name must be registered with references to their Collection and
# Playlist implementations.
PLATFORM_REGISTRY = {
    "rekordbox": {
        "collection": RekordboxCollection,
        "playlist": RekordboxPlaylist,
    }
}


def build_tag_playlists(
    content: Union[PlaylistConfigContent, str],
    tags_tracks: Dict[str, Dict[str, Track]],
    playlist_class: Playlist,
    tag_set: Optional[Set] = None,
) -> Union[None, Playlist]:
    """Recursively traverses a playlist config to generate playlists from tags.

    Args:
        content: A component of a playlist config to create a playlist for.
        tags_tracks: Dict of tags to tracks.
        playlist_class: Playlist implementation class.
        tag_set: A set of tags seen while creating playlists. This is used to
            indicate which tags should be ignored when creating the "Other"
            playlists.

    Raises:
        ValueError: The user's playlist config must not be malformed.

    Returns:
        A Playlist or None.
    """
    # Initialize the set of tags in case the caller didn't provide one.
    tag_set = tag_set if tag_set is not None else set()

    # This is not a folder so a playlist with tracks must be created.
    if isinstance(content, str):
        # Apply special logic for creating a "pure" playlist. "Pure" playlists
        # are those that contain tracks with a set of genre tags that all
        # contain the sub-string indicated by the suffix of the playlist name.
        # For example, "Pure Techno" will contain tracks that have genres
        # {"Hard Techno", "Melodic Techno"} but will not contain tracks that
        # contain {"Hard Techno", "Tech House"} because "Tech House" does not
        # contain "Techno" as a sub-string.
        if content.startswith("Pure "):
            # Isolate the tag to create a pure playlist for.
            tag = content.split("Pure ")[-1]
            tracks_with_tag = tags_tracks.get(tag)
            if not tracks_with_tag:
                logger.warning(
                    f'Can\'t make a "Pure {tag}" playlist because there are '
                    "no tracks with that tag."
                )
                return None

            # Filter out tracks that aren't pure.
            pure_tag_tracks = {
                track_id: track for track_id, track in tracks_with_tag.items()
                if all(
                    tag.lower() in _.lower() for _ in track.get_genre_tags()
                )
            }
            if not pure_tag_tracks:
                logger.warning(
                    f'Can\'t make a "Pure {tag}" playlist because there are '
                    f"no tracks that are pure {tag}."
                )
                return None

            return playlist_class.new_playlist(
                name=content, tracks=pure_tag_tracks
            )

        # Get tracks with this tag and index it so that it's not added to the
        # "Other" playlists.
        tracks_with_tag = tags_tracks.get(content)
        tag_set.add(content)
        if not tracks_with_tag:
            logger.warning(f'There are no tracks with the tag "{content}"')
            return None

        return playlist_class.new_playlist(
            name=content, tracks=tracks_with_tag
        )

    # This is a folder so create playlists for those playlists within it.
    if isinstance(content, PlaylistConfigContent):
        # Update the set of tags seen so these are ignored in when creating the
        # "Other" playlists.
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
            name=content.name, playlists=playlists,
        )

    raise ValueError(f"Invalid input type {type(content)}: {content}")


class PlaylistFilter(ABC):
    "This class defines an interface for filtering tracks from playlists."

    @abstractmethod
    def filter_track(self, track: Track) -> bool:
        """Returns True if this track should remain in the playlist.

        Args:
            track: Track object to apply filter to.

        Returns:
            Whether or not this track should be included in the playlist.
        """

    @abstractmethod
    def is_filter_playlist(self, playlist: Playlist) -> bool:
        """Returns True if this playlist should be filtered.

        Args:
            playlist: Playlist object to potentially filter.

        Returns:
            Whether or not to filter this playlist.
        """


class HipHopFilter(PlaylistFilter):
    'This class filters playlists called "Hip Hop".'

    def filter_track(self, track: Track) -> bool:
        """Returns True if this track should remain in the playlist.

        If the playlist is not underneath a folder called "Bass", then this
        track is filtered out unless it has exclusively "Hip Hop" and "R&B"
        genre tags. If the playlist is underneath a folder called "Bass", then
        this track is filtered out if it does have exclusively "Hip Hop" and
        "R&B" genre tags.

        Args:
            track: Track object to apply filter to.

        Returns:
            Whether or not this track should be included in the playlist.
        """
        pure_hip_hop_with_other_tags = not self._bass_hip_hop and any(
            "r&b" not in x.lower() and "hip hop" not in x.lower()
            for x in track.get_genre_tags()
        )
        bass_hip_hop_without_other_tags = self._bass_hip_hop and all(
            "r&b" in x.lower() or "hip hop" in x.lower()
            for x in track.get_genre_tags()
        )
        if pure_hip_hop_with_other_tags or bass_hip_hop_without_other_tags:
            return False

        return True


    def is_filter_playlist(self, playlist: Playlist) -> bool:
        """Returns True if this playlist's name is "Hip Hop".

        Args:
            playlist: Playlist object to potentially filter.

        Returns:
            Whether or not to filter this playlist.
        """
        if not playlist.get_name() == "Hip Hop":
            return False

        self._bass_hip_hop = False  #pylint: disable=attribute-defined-outside-init
        parent = playlist.get_parent()
        while parent:
            if parent.get_name() == "Bass":
                self._bass_hip_hop = True  #pylint: disable=attribute-defined-outside-init
            parent = parent.get_parent()

        return True


class MinimalDeepTechFilter(PlaylistFilter):
    'This class filters playlists called "Minimal Deep Tech".'

    def filter_track(self, track: Track) -> bool:
        """Returns True if this track should remain in the playlist.

        If the playlist is not underneath a folder called "Techno", then this
        track is filtered out if the genre tag preceding "Minimal Deep Tech" is
        "Techno". If the playlist is underneath a folder called "Techno", then
        this track is filtered out if the genre tag preceding
        "Minimal Deep Tech" is not "Techno".

        Args:
            track: Track object to apply filter to.

        Returns:
            Whether or not this track should be included in the playlist.
        """
        genre_tags = track.get_genre_tags()
        index = genre_tags.index("Minimal Deep Tech")
        prefix_tag = genre_tags[index - 1]
        techno_with_no_techno_prefix = (
            self._techno and prefix_tag.lower() != "techno"
        )
        not_techno_with_techno_prefix = (
            not self._techno and prefix_tag.lower() == "techno"
        )
        if techno_with_no_techno_prefix or not_techno_with_techno_prefix:
            return False

        return True

    def is_filter_playlist(self, playlist: Playlist) -> bool:
        """Returns True if this playlist's name is "Minimal Deep Tech".

        Args:
            playlist: Playlist object to potentially filter.

        Returns:
            Whether or not to filter this playlist.
        """
        if not playlist.get_name() == "Minimal Deep Tech":
            return False

        self._techno = False  #pylint: disable=attribute-defined-outside-init
        parent = playlist.get_parent()
        while parent:
            if parent.get_name() == "Techno":
                self._techno = True  #pylint: disable=attribute-defined-outside-init
            parent = parent.get_parent()

        return True


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
            tracks = {
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
        track_id: track for p in playlist
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
    playlist_config: PlaylistConfig,
    tags_tracks: Dict[str, Dict[str, Track]],
    collection: Collection,
    auto_playlists: List[Playlist],
):
    """Parse the Combiner playlists for selectors and update track lookup.

    Args:
        playlist_config: PlaylistConfig object.
        tags_tracks: Dict of tags to tracks.
        collection: Collection object.
        auto_playlists: Tag playlists built in this same run.
    """
    playlists = set()
    values_set = set()
    bpm_rating_lookup = {}
    playlist_selector_regex = r"(?<={)[^{}]*(?=})"
    bpm_rating_selector_regex = r"(?<=\[)[^\[\]]*(?=\])"

    # Grab selectors from Combiner playlists' names.
    for playlist in playlist_config.combiner.playlists:
        playlists.update(re.findall(playlist_selector_regex, playlist))
        bpm_rating_matches = re.findall(bpm_rating_selector_regex, playlist)
        if not bpm_rating_matches:
            continue
        parsed_bpms, parsed_ratings = parse_bpms_and_ratings(
            bpm_rating_matches, bpm_rating_lookup
        )
        values_set.update(parsed_bpms)
        values_set.update(parsed_ratings)

    # Add keys for BPM and rating selectors for tracks having those values.
    for track_id, track in collection.get_tracks().items():
        values = map(str, [round(track.get_bpm()), track.get_rating()])
        for val in values:
            if val not in values_set:
                continue
            for value, tag in bpm_rating_lookup.items():
                if (
                    (isinstance(value, str) and value == val) or
                    (isinstance(value, tuple) and val in value)
                ):
                    tags_tracks[tag][track_id] = track

    # Get playlists for the identified playlist selectors. Not only must we get
    # playlists from the collection, but we must also get playlists from the
    # auto playlists constructed in the very same run of the playlist_builder.
    # This is because the playlists being selected may include those generated
    # by the playlist_builder.
    for playlist_name in playlists:
        for playlist_object in [collection, *auto_playlists]:
            for playlist in playlist_object.get_playlists(playlist_name):
                tags_tracks[f"{{{playlist_name}}}"].update(
                    playlist.get_tracks()
                )


def parse_bpms_and_ratings(
    bpm_rating_match: List[str],
    bpm_rating_lookup: Dict[Union[str, Tuple], str],
) -> List[Tuple]:
    """Parses a string match of one or more BPM and / or rating selectors.

    Args:
        bpm_rating_match: List of BPM or rating strings.
        bpm_rating_lookup: Empty dict to populate with tuples or strings
            mapping bpm or rating ranges or values to their "tag"
            representation.

    Returns:
        Tuple of BPM and rating lists.
    """
    bpms, ratings = [], []
    for bpm_rating in bpm_rating_match:
        parts = map(str.strip, bpm_rating.split(","))
        for part in parts:
            number = _range = None
            # If "part" is a digit, then it's an explicit BPM or rating to
            # filter for.
            if part.isdigit():
                number = int(part)
                if 0 <= number <= 5:
                    ratings.append(str(number))
                elif number > 5:
                    bpms.append(str(number))
            # If "part" is two digits separated by a "-", then it's a range
            # of BPMs or ratings to filter for.
            elif (
                len(part.split("-")) == 2 and
                all(x.isdigit() for x in part.split("-"))
            ):
                _range = list(map(int, part.split("-")))
                _range = range(min(_range), max(_range) + 1)
                if all(0 <= x <= 5 for x in _range):
                    ratings.extend(map(str, _range))
                elif all(x > 5 for x in _range):
                    bpms.extend(map(str, _range))
                else:
                    logger.error(f"Bad BPM or rating number range: {part}")
                    continue
            else:
                logger.error(
                    f"Malformed BPM or rating filter part: {part}"
                )
                continue

            bpm_rating_lookup[
                tuple(map(str, _range or [])) or str(number)
            ] = f"[{part}]"

    return bpms, ratings


def build_combiner_playlists(
    playlist_config: PlaylistConfig,
    tags_tracks: Dict[str, Dict[str, Track]],
    playlist_class: Playlist,
) -> Playlist:
    """Creates Combiner playlists.

    Args:
        playlist_config: PlaylistConfig object.
        tags_tracks: Dict of tags to tracks.
        playlist_class: Playlist implementation class.

    Returns:
        Combiner playlists.
    """
    return playlist_class.new_playlist(
        name=playlist_config.combiner.name, playlists=[
            playlist_class.new_playlist(
                name=expression,
                tracks=parse_expression(expression, tags_tracks),
            )
            for expression in playlist_config.combiner.playlists
        ]
    )


def parse_expression(
    expression: str, tags_tracks: Dict[str, Dict[str, Track]]
) -> Playlist:
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
            tag = node.add_tag(tag)
            node.add_operator(char)
        elif char == ")":
            tag = node.add_tag(tag)
            tracks = node.evaluate()
            node = node.get_parent()
            if tracks:
                node.add_tracks(tracks)
        else:
            tag += char
    tag = node.add_tag(tag)

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
        self._tags = []
        self._tracks = []
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
        if "*" in tag:
            exp = re.compile(r".*".join(tag.split("*")))
            tracks = {}
            for key in self._tags_tracks:
                if re.search(exp, key):
                    tracks.update(self._tags_tracks[key])
            return tracks

        return self._tags_tracks.get(tag, {})

    def add_tag(self, tag: str) -> str:
        """Add tag to BooleanNode.

        Args:
            tag: Tag to be evaluated.

        Returns:
            Empty string to reset tag in the parse_expression function.
        """
        tag = tag.strip()
        if tag:
            self._tags.append(tag)

        return ""

    def add_operator(self, operator: str):
        """Adds a set operation to the BooleanNode.

        Args:
            operator: Character representing a set operation.
        """
        self._operators.append(self._ops[operator])

    def add_tracks(self, tracks: Dict[str, Track]):
        """Adds a dict of tracks to the BooleanNode.

        Args:
            tracks: Dict of tracks.
        """
        self._tracks.append(tracks)

    def evaluate(self) -> Dict[str, Track]:
        """Applies operators to the operands to produce a dict of tracks.

        Raises:
            RuntimeError: The boolean expression is malformed. It must contain
                one less operator than there are operands.

        Returns:
            A dict of tracks reduced from the boolean expression.
        """
        operators = len(self._operators)
        operands = len(self._tags) + len(self._tracks)
        if operators + 1 != operands:
            raise RuntimeError(
                "Invalid boolean expression: track sets: "
                f"{len(self._tracks)}, tags: {self._tags}, operators: "
                f"{[x.__name__ for x in self._operators]}"
            )
        while self._tags or self._operators:
            operator = self._operators.pop(0)
            tracks_a = (
                self._tracks.pop(0) if self._tracks else
                self._get_tracks(tag=self._tags.pop(0))
            )
            tracks_b = (
                self._tracks.pop(0) if self._tracks
                else self._get_tracks(tag=self._tags.pop(0))
            )
            track_ids = operator(set(tracks_a), set(tracks_b))
            tracks = {
                track_id: track
                for track_id, track in {**tracks_a, **tracks_b}.items()
                if track_id in track_ids
            }
            self._tracks.insert(0, tracks)

        return next(iter(self._tracks), set())

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
    for playlist in combiner_playlists:
        tracks = playlist.get_tracks()
        if tracks:
            print(f"\n{playlist.get_name()} tag statistics:")
        playlist_tags = defaultdict(int)
        genre_tags = set()
        other_tags = set()
        for track in tracks.values():
            track_all_tags = track.get_tags()
            track_genre_tags = set(track.get_genre_tags())
            other_tags.update(track_all_tags.difference(track_genre_tags))
            genre_tags.update(track_genre_tags)
            for tag in track_all_tags:
                playlist_tags[tag] += 1
        for tag_subset, tags in [
            ("Genre", sorted(genre_tags)), ("Other", sorted(other_tags))
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
        maximum: Upper bound for rescaled data.

    Returns:
        Rescaled dictionary of tag names and tag counts.
    """
    data_max = max(data.items(), key=itemgetter(1))[1]

    return {k: round((v / data_max) * maximum) for k, v in data.items()}


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
