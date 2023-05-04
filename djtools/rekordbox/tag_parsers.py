"""This module contains the abstract bass class, TagParser, and implementations
of TagParser.

A TagParser implementation is instantiated with a "parser_config" which
describes the taxonomy of folders and playlists to be constructed from
particular tags. An instantiated TagParser is called with a track and must
return a list of tags from which playlists are to be constructed.
"""
from abc import ABC, abstractmethod
import logging
import re
from typing import Dict, List, Optional, Union

import bs4


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
        self._kwargs = kwargs
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

class GenreTagParser(TagParser):
    """Parses the "Genre" field of a track to produce tags."""

    def __init__(
        self,
        parser_config: Dict[str, Union[str, List[Union[str, Dict]]]],
        pure_genre_playlists: Optional[List[str]] = None,
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
        super().__init__(parser_config, **kwargs)
        self._pure_playlists = pure_genre_playlists or []

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
