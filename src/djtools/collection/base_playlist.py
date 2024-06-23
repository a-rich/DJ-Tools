"""This module contains the base class for playlists of different DJ software
platforms.

Playlist is an abstract base class which defines the interface expected of a
playlist; namely methods for (de)serialization to/from the representation
recognized by the DJ software for which Playlist is being sub-classed.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import re
from typing import Any, Dict, List, Optional

from djtools.collection.base_track import Track


# pylint: disable=duplicate-code


class Playlist(ABC):
    "Abstract base class for a playlist."

    @abstractmethod
    def __init__(self, *args, **kwargs):
        "Deserializes a playlist from the native format of a DJ software."

    def __getitem__(self, index: int) -> Playlist:
        """Gets a Playlist from this Playlist's playlists.

        This method is used to iterate this object during serialization. If
        this Playlist is a folder, then it returns elements from
        self._playlists for serialization.

        Args:
            index: The index of the Playlist to get.

        Returns:
            A Playlist.
        """
        return self._playlists[index]

    def __len__(self) -> int:
        """Returns the number of elements in this Playlist.

        If this Playlist is a folder, it returns the number of Playlists within
        it. If this Playlist is instead an actual playlist, then it returns the
        number of Tracks it contains.

        Returns:
            The number of elements in this Playlist.
        """
        if self.is_folder():
            return len(self._playlists)
        return len(self._tracks)

    def add_playlist(self, playlist: Playlist, index: Optional[int] = None):
        """Adds a playlist to this folder-type playlist.

        Args:
            playlist: Playlist to add.
            index: Insert the playlist at a specific index.

        Raises:
            RuntimeError: Only folder Playlists can be added to.
        """
        if not self.is_folder():
            raise RuntimeError("You can't append to a non-folder Playlist")
        if index is not None:
            self._playlists.insert(index, playlist)
        else:
            self._playlists.append(playlist)

    @abstractmethod
    def get_name(self) -> str:
        """Returns the name of this playlist.

        Returns:
            The name of this playlist.
        """

    def get_parent(self) -> Optional[Playlist]:
        """Returns the folder this playlist is in.

        Returns:
            A Playlist folder or None (if no parent).
        """
        return self._parent

    def get_playlists(
        self, name: Optional[str] = None, glob: Optional[bool] = False
    ) -> List[Playlist]:
        """Returns Playlists with a matching name.

        Args:
            name: Name of the Playlists to return.
            glob: Glob on playlist name containing "*".

        Returns:
            The Playlists with the same name.
        """
        if not name:
            if not self.is_folder():
                raise RuntimeError(
                    f'Playlist "{self.get_name()}" is not a folder so you '
                    f"cannot call get_playlists on it."
                )
            return list(self)

        exp = re.compile(r".*".join(name.split("*")))
        playlists = []
        if (glob and re.search(exp, self.get_name())) or (
            not glob and self.get_name() == name
        ):
            playlists.append(self)
        if self.is_folder():
            for playlist in self:
                playlists.extend(playlist.get_playlists(name, glob=glob))

        return [playlist for playlist in playlists if playlist is not None]

    def get_tracks(self) -> Dict[str, Track]:
        """Returns a dict of track IDs and tracks.

        Returns:
            A dict of track IDs and tracks.
        """
        return self._tracks

    @abstractmethod
    def is_folder(self) -> bool:
        """Returns whether this playlist is a folder or a playlist of tracks.

        Returns:
            Boolean representing whether this is a folder or not.
        """

    @classmethod
    @abstractmethod
    def new_playlist(
        cls,
        name: str,
        playlists: Optional[List[Playlist]] = None,
        tracks: Optional[Dict[str, Track]] = None,
    ) -> Playlist:
        """Creates a new Playlist.

        Args:
            name: The name of the Playlist to be created.
            playlists: A list of Playlists to add to this Playlist.
            tracks: A dict of Tracks to add to this Playlist.

        Raises:
            RuntimeError: You must provide either a list of Playlists or a list
                of Tracks.
            RuntimeError: You must not provide both a list of Playlists and a
                list of Tracks.

        Returns:
            A new Playlist.
        """

    def remove_playlist(self, playlist: Playlist):
        """Removes playlist from list of playlists.

        Args:
            playlist: Playlist to remove.

        Raises:
            RuntimeError: Can't remove playlist from a non-folder playlist.
        """
        if not self.is_folder():
            raise RuntimeError(
                "Can't remove playlist from a non-folder playlist."
            )
        self._playlists = [  # pylint: disable=attribute-defined-outside-init
            _playlist
            for _playlist in self._playlists
            if _playlist is not playlist
        ]

    @abstractmethod
    def serialize(self, *args, **kwargs) -> Any:
        """Serializes a playlist into the native format of a DJ software.

        Returns:
            A serialized playlist of the same type used to initialized
                Playlist.
        """

    def set_parent(self, parent: Optional[Playlist] = None):
        """Recursively sets the parent of all playlists within.

        Args:
            parent: Playlist to set as the parent.
        """
        self._parent = parent  # pylint: disable=attribute-defined-outside-init
        if not self.is_folder():
            return
        for child in self:
            child.set_parent(self)

    def set_tracks(self, tracks: Dict[str, Track]):
        """Sets the tracks of this playlist.

        Args:
            tracks: A dict of Tracks to override for this Playlist.
        """
        self._tracks = tracks  # pylint: disable=attribute-defined-outside-init
