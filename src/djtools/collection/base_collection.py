"""This module contains the base class for collections of different DJ software
platforms.

Collection is an abstract base class which defines the interface expected of a
collection; namely methods for (de)serialization to/from the representation
recognized by the DJ software for which Collection is being sub-classed.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
import re
from typing import Dict, List, Optional, Union

from djtools.collection.base_playlist import Playlist
from djtools.collection.base_track import Track


class Collection(ABC):
    "Abstract base class for a collection."

    @abstractmethod
    def __init__(self, path: Path, *args, **kwargs):
        """Deserializes a collection from the native format of a DJ software.

        Args:
            path: Path to a serialized collection.
        """

    def add_playlist(self, playlist: Playlist):
        """Appends a playlist to the collection.

        Args:
            playlist: Playlist to append to the collection.
        """
        self._playlists.add_playlist(playlist)  # pylint:disable=no-member

    def get_all_tags(self) -> Dict[str, List[str]]:
        """Returns the all tags in the collection.

        Returns:
            Dict containing all track tags keyed by "genres" and "other".
        """
        all_tags = {
            tag
            for track in self.get_tracks().values()
            for tag in track.get_tags()
        }
        genre_tags = {
            tag
            for track in self.get_tracks().values()
            for tag in track.get_genre_tags()
        }
        other_tags = all_tags.difference(genre_tags)

        return {"genres": sorted(genre_tags), "other": sorted(other_tags)}

    def get_playlists(
        self, name: Optional[str] = None, glob: Optional[bool] = False
    ) -> Union[Playlist, List[Playlist]]:
        """Returns Playlists with a matching name.

        If no playlist name is provided, then the root playlist is returned.

        Args:
            name: Name of the Playlists to return.
            glob: Glob on playlist name containing "*".

        Returns:
            The Playlists with the same name.
        """
        if not name:
            return self._playlists  # pylint:disable=no-member

        exp = re.compile(r".*".join(name.split("*")))
        playlists = []
        for playlist in self._playlists:  # pylint:disable=no-member
            if (glob and re.search(exp, playlist.get_name())) or (
                not glob and playlist.get_name() == name
            ):
                playlists.append(playlist)
            if playlist.is_folder():
                for playlist in playlist:
                    playlists.extend(playlist.get_playlists(name, glob=glob))

        return [playlist for playlist in playlists if playlist is not None]

    def get_tracks(self) -> Dict[str, Track]:
        """Returns the tracks in the collection.

        Returns:
            Dict of tracks.
        """
        return self._tracks

    @abstractmethod
    def serialize(self, *args, **kwargs) -> Path:
        """Serialize a collection into the native format of a DJ software.

        Returns:
            A path to a serialized collection.
        """

    def set_tracks(self, tracks: Dict[str, Track]):
        """Sets the tracks of this collection.

        Args:
            tracks: Tracks to set.
        """
        self._tracks = tracks  # pylint:disable=attribute-defined-outside-init
