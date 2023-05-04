"""The "Combiner" constructs Rekordbox playlists by evaluating arbitrary
boolean algebra expressions provided as the playlist name.

The supported operands are:

- string literals matching one of the possible returned tags from a TagParser
    implementation (see GenreTagParser and MyTagParser)
- playlist names enclosed in curly braces e.g. {My Favorites}
- ratings in the inclusive range [0, 5], separated by commas with ranges
    denoted using a dash; both styles are enclosed with square brackets e.g.
    [0, 2-5]
- BPMs in the inclusive range [6, inf], separated by commas with ranges denoted
    using a dash; both styles are enclosed with square brackets e.g.
    [80-90, 140, 160-180]

NOTE: the use of an asterisk `*` in an operand will glob other tags. For
example, the providing "* Techno" as an operand would match "Acid Techno" and
"Hard Techno" but not "somethingTechno" (because of the space character).
Providing "Deep *" as an operand would match "Deep House" as well as
"Deep Dubstep".

The supported operators are:

- `&` a.k.a. AND a.k.a set intersection: resulting tracks must be in BOTH sets
- `|` a.k.a. OR a.k.a set union: resulting tracks may be in EITHER sets
- `~` a.k.a. NOT a.k.a set difference: resulting tracks are those from the
    left-hand side of the operator with the tracks appearing on the right-hand
    side of the operator removed
- `(`, `)`: parentheses are used to control the order of operations

Some example expressions:

- "(([120-129] & *Techno) | [130-160]) ~ [5]" This will first match all tracks
    in the BPM range 120-129 inclusive before intersecting those with tracks
    with a tag containing "Techno" as a suffix before unioning with all tracks
    in the BPM range 130-160. Lastly, any tracks having a rating of 5 are
    removed from the playlist.
- "(Chill | Melodic) ~ {All Bass}" This will first take the union of all tracks
    with either a "Chill" tag or a "Melodic" tag before removing all tracks
    that appear in a playlist called "All Bass".

The "Combiner" configuration must specify a flat list of "playlists" which
define the boolean algebra expressions used by the Combiner.
"""
from collections import defaultdict
import logging
import re
from typing import Dict, List, Set, Tuple, Union

from bs4 import BeautifulSoup

from djtools.rekordbox.helpers import BooleanNode


logger = logging.getLogger(__name__)


class Combiner:
    """Parses a boolean algebra expression to combine tag playlists."""

    def __init__(
        self,
        parser_config: Dict[str, Union[str, List[Union[str, Dict]]]],
        rekordbox_database: BeautifulSoup,
    ):
        """Constructor.

        Args:
            parser_config: YAML playlist structure.
        """
        self.parser_config = parser_config
        self._tracks = defaultdict(lambda: defaultdict(list))
        self._bpm_rating_lookup = {}
        self._prescan(rekordbox_database)
        self._operators = {
            "&": set.intersection,
            "|": set.union,
            "~": set.difference,
        }

    def __call__(
        self, tracks: Dict[str, List[Tuple[str, List[str]]]]
    ) -> Dict[str, Set[str]]:
        """Evaluates boolean expressions creating playlists that combine tags.

        Args:
            tracks: Map of tags to lists of (track_id, tags) tuples.

        Returns:
            Dict mapping boolean expression to a set of track IDs.
        """
        self._tracks.update({k: dict(v) for k, v in tracks.items()})
        playlist_tracks = {
            expression: self._parse_boolean_expression(expression)
            for expression in self.parser_config.get("playlists", [])
        }

        return playlist_tracks

    def _add_tag(self, tag: str, node: BooleanNode) -> str:
        """Strips whitespace off of a tag and, if non-empty, adds it to a node.

        Args:
            tag: Potentially assembled tag string.
            node: BooleanNode to potentially have tag added to it.

        Returns:
            Empty tag string.
        """
        tag = tag.strip()
        if tag:
            node.tags.append(tag)

        return ""

    def get_combiner_tracks(self) -> Dict[str, Dict[str, List]]:
        """Returns tag / selector -> tracks mapping.

        Returns:
            Map of tags / selectors to track_id.
        """
        return self._tracks

    def get_playlist_mapping(
        self,
        rekordbox_database: BeautifulSoup,
    ) -> Dict[str, List[Tuple[str, List]]]:
        """Adds tags for playlist selectors.

        Args:
            rekordbox_database: Parsed XML.

        Raises:
            LookupError: Playlists in expressions must exist in "XML_PATH".

        Returns:
            Map of playlist selectors to (track_id, tags) tuples.
        """
        for playlist_name in self._playlists:
            try:
                playlist = rekordbox_database.find_all(
                    "NODE", {"Name": playlist_name}
                )[0]
            except IndexError:
                raise LookupError(f"{playlist_name} not found") from LookupError

            self._tracks[f"{{{playlist_name}}}"] = {
                track["Key"]: [] for track in playlist.children
                if str(track).strip()
            }

        return self._tracks

    def _parse_boolean_expression(self, expression: str) -> Set[str]:
        """Parses a boolean algebra expression by constructing a tree.

        Args:
            expression: String representing boolean algebra expression.

        Returns:
            Set of track IDs reduced from the evaluation of the expression.
        """
        node = BooleanNode()
        tag = ""
        for char in expression:
            if char == "(":
                node = BooleanNode(parent=node)
            elif char in self._operators:
                tag = self._add_tag(tag, node)
                node.operators.append(self._operators[char])
            elif char == ")":
                tag = self._add_tag(tag, node)
                tracks = node(self._tracks)
                node = node.parent
                if tracks:
                    node.tracks.append(tracks)
            else:
                tag += char
        tag = self._add_tag(tag, node)

        return node(self._tracks)

    def _parse_bpms_and_ratings(
        self, bpm_rating_match: List[str]
    ) -> List[Tuple]:
        """Parses a string match of one or more BPM and / or rating selectors.

        Args:
            bpm_rating_match: List of BPM or rating strings.

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

                self._bpm_rating_lookup[
                    tuple(map(str, _range or [])) or str(number)
                ] = f"[{part}]"

        return bpms, ratings

    def _prescan(self, rekordbox_database: BeautifulSoup):
        """Populates track lookup using BPM and rating selectors.

        Boolean expressions may contain zero or more indicators for selectors:
            * BPM selectors: comma-delimited list of integers or integer ranges
                (e.g. "6-666") greater than 5 enclosed in square brackets
                (e.g. "[120, 137-143]").
            * Rating selectors: comma-delimited list of integers or integer
                ranges (e.g. "0-5") less than 6 enclosed in square brackets
                (e.g. "[5, 2, 2-4]").
            * Playlist selectors: exact matches to existing playlist name
                enclosed in curly braces (e.g. "{All DnB}").
        
        Whether the numbers of a BPM / rating selector are interpreted as a BPM
        or a rating depends on the value; if 0 <= number <= 5, then it's
        interpreted as a rating, if number > 5, then it's interpreted as a BPM.

        This method also initializes a set of playlist selectors but delays
        populating them until any other TagParser implementations have been
        called so as to ensure the Combiner logic evaluation includes the
        complete set of tracks that may have been added to playlists by these
        TagParsers.
            
        If you want to make a Combiner playlist that has all tracks in a
        playlist called "All DnB" that have a 5 star rating and are in the BPM
        range [170, 172], this can be expressed as:
            "{All DnB} & [5, 170-172]"

        Args:
            rekordbox_database: Parsed XML.

        Raises:
            LookupError: Playlists in expressions must exist in "XML_PATH".
        """
        # Get the sets of BPMs, ratings, and playlists in order to pre-populate
        # the track lookup.
        bpms, ratings, self._playlists = set(), set(), set()
        for expression in self.parser_config.get("playlists", []):
            self._playlists.update(re.findall(r"(?<={)[^{}]*(?=})", expression))
            bpm_rating_match = re.findall(r"(?<=\[)[^\[\]]*(?=\])", expression)
            if not bpm_rating_match:
                continue
            _bpms, _ratings = self._parse_bpms_and_ratings(bpm_rating_match)
            bpms.update(_bpms)
            ratings.update(_ratings)

        # Rekordbox stores rating values in the range [0, 255].
        ratings_value_lookup = {
            "0": "0",
            "51": "1",
            "102": "2",
            "153": "3",
            "204": "4",
            "255": "5",
        }

        # Build out the lookup for BPMs and ratings.
        values_set = bpms.union(ratings)
        for track in rekordbox_database.find_all("TRACK"):
            if not track.get("Location"):
                continue

            values = [
                str(round(float(track["AverageBpm"]))),
                ratings_value_lookup[track["Rating"]]
            ]
            for val in values:
                if val in values_set:
                    for value, tag in self._bpm_rating_lookup.items():
                        if (
                            (isinstance(value, str) and value == val) or
                            (isinstance(value, tuple) and val in value)
                        ):
                            self._tracks[tag][track["TrackID"]] = []
