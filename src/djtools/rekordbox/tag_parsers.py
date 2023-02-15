"""This module contains the abstract bass class, TagParser, and implementations
of TagParser.

A TagParser implementation is instantiated with a "parser_config" which
describes the taxonomy of folders and playlists to be constructed from
particular tags. An instantiated TagParser is called with a track and must
return a list of tags from which playlists are to be constructed.

In addition to these, a special "Combiner" TagParser may be configured. The
"Combiner" configuration must specify a flat list of "playlists" which are
defined as boolean algebra expressions which combine any of the tags generated
by the other TagParsers ("Combiner" runs after the other TagParsers).
"""
from abc import ABC, abstractmethod
from collections import defaultdict
import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Union

import bs4
from bs4 import BeautifulSoup

from djtools.rekordbox.helpers import BooleanNode


logger = logging.getLogger(__name__)


class TagParser(ABC):
    """Abstract base class for parsing tags from a Rekordbox database."""

    def __init__(
        self,
        parser_config: Dict[str, Union[str, List[Union[str, Dict]]]],
        **kwargs,
    ):
        """Constructor.

        Args:
            parser_config: YAML playlist structure.
        """
        self.parser_config = parser_config

    @abstractmethod
    def __call__(self, track: bs4.element.Tag) -> List[str]:
        """Produces a list of tags from a track.

        Args:
            track: A track from a Rekordbox database.

        Raises:
            NotImplementedError: Implementations must define tag parsing.

        Returns:
            List of tags.
        """
        raise NotImplementedError(
            "Classes inheriting from TagParser must override the __call__ method."
        )


class Combiner(TagParser):
    """Parses a boolean algebra expression to combine tag playlists."""

    def __init__(
        self,
        parser_config: Dict[str, Union[str, List[Union[str, Dict]]]],
        rekordbox_database: BeautifulSoup,
        **kwargs,
    ):
        """Constructor.

        Args:
            parser_config: YAML playlist structure.
        """
        super().__init__(parser_config, **kwargs)
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
            Set of track IDs reduced from the evaulation of the expression.
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
                        logger.error(
                            "Bad BPM or rating number range: {}".format(part)
                        )
                        continue
                else:
                    logger.error(
                        "Malformed BPM or rating filter part: {}".format(part)
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


class GenreTagParser(TagParser):
    """Parses the "Genre" field of a track to produce tags."""

    def __init__(
        self,
        parser_config: Dict[str, Union[str, List[Union[str, Dict]]]],
        pure_genre_playlists: Optional[List[str]] = list(),
        **kwargs,
    ):
        """Constructor.

        Args:
            parser_config: YAML playlist structure.
            pure_genre_playlists: List of genre tags from which "pure"
                playlists will be generated. A "pure" playlist is one in which
                every track has genre tags which all contain a corresponding
                element in this list.
        """
        super().__init__(parser_config)
        self._pure_playlists = pure_genre_playlists

    def __call__(self, track: bs4.element.Tag) -> List[str]:
        """Produces a list of genre tags from a track.

        Args:
            track: A track from a Rekordbox database.

        Returns:
            List of genre tags.
        """
        tags = [x.strip() for x in track["Genre"].split("/")]
        for genre in self._pure_playlists:
            if all(genre.lower() in x.lower() for x in tags):
                tags.append(f"Pure {genre}")
        
        return tags


class MyTagParser(TagParser):
    """Parses the "Comments" field of a track to produce tags."""

    def __init__(
        self,
        parser_config: Dict[str, Union[str, List[Union[str, Dict]]]],
        **kwargs,
    ):
        """Constructor.

        Args:
            parser_config: YAML playlist structure.
        """
        super().__init__(parser_config, **kwargs)
        self._regex = re.compile(r"(?<=\/\*).*(?=\*\/)")

    def __call__(self, track: bs4.element.Tag) -> List[str]:
        """Produces a list of "My Tags" tags from a track.

        Args:
            track: A track from a Rekordbox database.

        Returns:
            List of "My Tags" tags.
        """
        tags = re.search(self._regex, track.get("Comments"))
        if not tags:
            return []

        return [x.strip() for x in tags.group().split("/")]
