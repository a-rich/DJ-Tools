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
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import bs4


class TagParser(ABC):
    """Abstract base class for parsing tags from a Rekordbox database."""

    def __init__(
        self,
        parser_config: Dict[str, Union[str, List[Union[str, Dict]]]],
        **kwargs,
    ):
        """Constructor.

        Args:
            parser_config: JSON playlist structure.
        """
        self.parser_config = parser_config

    @abstractmethod
    def __call__(self, track: bs4.element.Tag) -> List[str]:
        """Produces a list of tags from a track.

        Args:
            track: A track from a Rekordbox database.

        Raises:
            NotImplemented: Implementations must define tag parsing.

        Returns:
            List of tags.
        """
        raise NotImplemented(
            "Classes inheriting from TagParser must override the __call__ method."
        )


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
            parser_config: JSON playlist structure.
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
            parser_config: JSON playlist structure.
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


class BooleanNode:
    """Node that contains boolean logic for a subexpression."""

    def __init__(self, parent: Optional[Any] = None):
        """Constructor.

        Args:
            parent: BooleanNode of which this node is a subexpression.
        """
        self.parent = parent
        self.operators = []
        self.tags = []
        self.tracks = []
    
    def __call__(
        self, tracks: Dict[str, List[Tuple[str, List[str]]]]
    ) -> Set[str]:
        """Evaluates the boolean algebraic subexpression.

        Args:
            tracks: Map of tags to lists of (track_id, tags) tuples.

        Raises:
            RuntimeError: Boolean expressions must be formatted correctly.

        Returns:
            Reduced set of track IDs.
        """
        operators = len(self.operators)
        operands = len(self.tags) + len(self.tracks)
        if operators + 1 != operands:
            raise RuntimeError(
                f"Invalid boolean expression: track sets: {len(self.tracks)}, "
                f"tags: {self.tags}, operators: "
                f"{[x.__name__ for x in self.operators]}"
            )
        while self.tags or self.operators:
            operator = self.operators.pop(0)
            if len(self.tracks):
                tracks_A = self.tracks.pop(0)
            else:
                tracks_A = self._get_tag_tracks(
                    tag=self.tags.pop(0), tracks=tracks
                )
            if len(self.tracks):
                tracks_B = self.tracks.pop(0)
            else:
                tracks_B = self._get_tag_tracks(
                    tag=self.tags.pop(0), tracks=tracks
                )
            self.tracks.insert(0, operator(tracks_A, tracks_B))
        
        return next(iter(self.tracks), set())

    def _get_tag_tracks(
        self, tag: str, tracks: Dict[str, List[Tuple[str, List[str]]]]
    ) -> Set[str]:
        """Gets set of track IDs for the provided tag.

        If the tag contains a wildcard, denoted with "*", then the union of
        track IDs with a tag containing the provided tag as a substring is
        returned.

        Args:
            tag: Tag for indexing tracks.
            tracks: Map of tags to lists of (track_id, tags) tuples.

        Returns:
            Set of track IDs for the provided tag.
        """
        if "*" in tag:
            exp = re.compile(r".*".join(tag.split("*")))
            track_ids = set()
            for k in tracks:
                if re.search(exp, k):
                    track_ids.update(set(tracks[k].keys()))
            return track_ids
        else:
            return set(tracks.get(tag, {}).keys())


class Combiner(TagParser):
    """Parses a boolean algebra expression to combine tag playlists."""

    def __init__(
        self,
        parser_config: Dict[str, Union[str, List[Union[str, Dict]]]],
        **kwargs,
    ):
        """Constructor.

        Args:
            parser_config: JSON playlist structure.
        """
        super().__init__(parser_config, **kwargs)
        self._tracks = {}
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
        self._tracks = {k: dict(v) for k, v in tracks.items()}
        playlist_tracks = {
            expression: self._parse_boolean_expression(expression)
            for expression in self.parser_config.get("playlists", [])
        }
        
        return playlist_tracks

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
