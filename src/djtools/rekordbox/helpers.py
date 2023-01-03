"""This module contains helpers for the rekordbox package."""
import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import bs4
from bs4 import BeautifulSoup


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
            tracks: Map of tags to dicts of track_id: tags.

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


def get_playlist_track_locations(
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


def rewrite_xml(config: Dict[str, Union[List, Dict, str, bool, int, float]]):
    """This function modifies the "Location" field of track tags in a
        downloaded Rekordbox XML replacing the "USB_PATH" written by
        "XML_IMPORT_USER" with the "USB_PATH" in "config.json".

    Args:
        config: Configuration object.

    Raises:
        KeyError: "XML_PATH" must be configured.
    """
    xml_path = config.get("XML_PATH")
    if not xml_path:
        raise ValueError(
            "Using the sync_operations module's download_xml function "
            "requires the config option XML_PATH"
        )

    registered_users_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "configs",
        "registered_users.json",
    ).replace(os.sep, "/")

    with open(registered_users_path, mode="r", encoding="utf-8") as _file:
        registered_users = json.load(_file)
        src = registered_users[config["XML_IMPORT_USER"]].strip("/")
        dst = registered_users[config["USER"]].strip("/")

    xml_path = os.path.join(
        os.path.dirname(xml_path),
        f'{config["XML_IMPORT_USER"]}_rekordbox.xml',
    ).replace(os.sep, "/")

    with open(xml_path, mode="r", encoding="utf-8") as _file:
        soup = BeautifulSoup(_file.read(), "xml")
        for track in soup.find_all("TRACK"):
            if not track.get("Location"):
                continue
            track["Location"] = track["Location"].replace(src, dst)

    with open(xml_path, mode="wb", encoding=soup.orignal_encoding) as _file:
        _file.write(soup.prettify("utf-8"))


def set_tag(track: str, index: int):
    """Threaded process to set TRACK node's TrackNumber tag.

    Args:
        track: TRACK node.
        index: New TrackNumber.
    """
    track["TrackNumber"] = index


def wrap_playlists(soup: BeautifulSoup, randomized_tracks: List[bs4.element.Tag]):
    """Creates a playlist called "AUTO_RANDOMIZE", inserts the randomized
        tracks into it, and then inserts "AUTO_RANDOMIZE" into the root of the
        "Playlist" folder.

    Args:
        soup: Parsed XML.
        randomized_tracks: Track nodes.
    """
    playlists_root = soup.find_all("NODE", {"Name": "ROOT", "Type": "0"})[0]
    new_playlist = soup.new_tag(
        "NODE", KeyType="0", Name="AUTO_RANDOMIZE", Type="1"
    )
    for track in randomized_tracks:
        new_playlist.append(soup.new_tag("TRACK", Key=track["TrackID"]))
    playlists_root.insert(0, new_playlist)
