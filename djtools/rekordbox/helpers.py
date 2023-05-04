"""This module contains helpers for the rekordbox package."""
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import unquote

import bs4
from bs4 import BeautifulSoup


class BooleanNode:
    """Node that contains boolean logic for a sub-expression."""

    def __init__(self, parent: Optional[Any] = None):
        """Constructor.

        Args:
            parent: BooleanNode of which this node is a sub-expression.
        """
        self.parent = parent
        self.operators = []
        self.tags = []
        self.tracks = []

    def __call__(
        self, tracks: Dict[str, List[Tuple[str, List[str]]]]
    ) -> Set[str]:
        """Evaluates the boolean algebraic sub-expression.

        Args:
            tracks: Map of tags to dicts of track_id: tags.

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
            if self.tracks:
                tracks_set_a = self.tracks.pop(0)
            else:
                tracks_set_a = self._get_tag_tracks(
                    tag=self.tags.pop(0), tracks=tracks
                )
            if self.tracks:
                tracks_set_b = self.tracks.pop(0)
            else:
                tracks_set_b = self._get_tag_tracks(
                    tag=self.tags.pop(0), tracks=tracks
                )
            self.tracks.insert(0, operator(tracks_set_a, tracks_set_b))

        return next(iter(self.tracks), set())

    def _get_tag_tracks(
        self, tag: str, tracks: Dict[str, List[Tuple[str, List[str]]]]
    ) -> Set[str]:
        """Gets set of track IDs for the provided tag.

        If the tag contains a wildcard, denoted with "*", then the union of
        track IDs with a tag containing the provided tag as a sub-string is
        returned.

        Args:
            tag: Tag for indexing tracks.
            tracks: Map of tags to dicts of track_id: tags.

        Returns:
            Set of track IDs for the provided tag.
        """
        if "*" in tag:
            exp = re.compile(r".*".join(tag.split("*")))
            track_ids = set()
            for key in tracks:
                if re.search(exp, key):
                    track_ids.update(set(tracks[key].keys()))
            return track_ids

        return set(tracks.get(tag, {}).keys())


def copy_file(
    track: bs4.element.Tag,
    destination: Path,
    loc_prefix: str="file://localhost",
):
    """Copies tracks to a destination and writes new Location field.

    Args:
        track: TRACK node from XML.
        destination: Directory to copy tracks to.
        loc_prefix: Location field prefix.
    """
    loc = Path(unquote(track["Location"]).split(loc_prefix)[-1])
    new_loc = Path(destination / loc.name).as_posix()
    shutil.copyfile(loc.as_posix(), new_loc)
    track["Location"] = f"{loc_prefix}{new_loc}"


def get_playlist_tracks(
    soup: BeautifulSoup, _playlist: str, seen_tracks: Set[str]
) -> List[str]:
    """Finds playlist in "XML_PATH" that matches "_playlist" and returns a list
        of the track nodes in that playlist that aren't in "seen_tracks".

    Args:
        soup: Parsed XML.
        _playlist: Name of playlist to randomize.
        seen_tracks: Already seen TrackIDs.

    Raises:
        LookupError: "_playlist" must exist.

    Returns:
        TrackIDs.
    """
    try:
        playlist = soup.find_all("NODE", {"Name": _playlist})[0]
    except IndexError:
        raise LookupError(f"{_playlist} not found") from LookupError

    playlist_tracks = [
        track["Key"] for track in playlist.children
        if str(track).strip() and track["Key"] not in seen_tracks
    ]
    seen_tracks.update(playlist_tracks)

    return playlist_tracks


def set_track_number(track: str, index: int):
    """Threaded process to set TRACK node's TrackNumber tag.

    Args:
        track: TRACK node.
        index: New TrackNumber.
    """
    track["TrackNumber"] = index
