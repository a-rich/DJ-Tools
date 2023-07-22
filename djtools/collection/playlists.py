"""This module contains classes for playlists of different DJ software
platforms.

Playlist is an abstract base class which defines the interface expected of a
playlist; namely methods for (de)serialization to/from the representation
recognized by the DJ software for which Playlist is being sub-classed. 

RekordboxPlaylist is an implementation of Playlist which operates on the XML
format that Rekordbox exports.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional

import bs4

from djtools.collection.tracks import RekordboxTrack, Track


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

    def add_playlist(
        self, playlist: Playlist, index: Optional[int] = None
    ):
        """Adds a playlist to this folder-type playlist.

        Args:
            playlist: Playlist to add.
            index: Insert the playlist at a specific index.

        Raises:
            RuntimeError: Only folder Playlists can be added to.
        """
        if not self.is_folder():
            raise RuntimeError(
                "You can't append to a non-folder Playlist"
            )
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

    def get_playlists(self, name: Optional[str] = None) -> List[Playlist]:
        """Returns Playlists with a matching name.

        Args:
            name: Name of the Playlists to return.

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

        playlists = []
        if self.get_name() == name:
            playlists.append(self)
        if self.is_folder():
            for playlist in self:
                playlists.extend(playlist.get_playlists(name))

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
            _playlist for _playlist in self._playlists
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


class RekordboxPlaylist(Playlist):
    "Playlist implementation for usage with Rekordbox."

    def __init__(
        self,
        playlist: bs4.element.Tag,
        tracks: Dict[str, RekordboxTrack] = None,
        playlist_tracks: Optional[Dict[str, RekordboxTrack]] = None,
        parent: Optional[RekordboxPlaylist] = None
    ):
        """Deserialize a Playlist from a BeautifulSoup NODE Tag.

        Args:
            playlist: BeautifulSoup Tag representing a playlist.
            tracks: All the tracks in this collection.
            playlist_tracks: Tracks to set when initializing with new_playlist.
            parent: The folder this playlist is in.
        """
        self._tracks = None
        self._playlists = None
        self._parent = parent
        tracks = tracks or {}

        # Set this object's attributes with the NODE Tag's attributes.
        for key, value in playlist.attrs.items():
            setattr(self, f"_{key}", value)

        # Recursively instantiate sub-playlists.
        if self.is_folder():
            self._playlists = [
                RekordboxPlaylist(playlist, tracks=tracks, parent=self)
                for playlist in filter(
                    lambda x: isinstance(x, bs4.element.Tag), playlist.children
                )
            ]
        # Deserialize tracks from a leaf node playlist.
        else:
            # Filter the children elements for Tags and get the key attribute.
            if not playlist_tracks:
                playlist_tracks = [
                    track.get("Key") for track in filter(
                        lambda x: isinstance(x, bs4.element.Tag),
                        playlist.children
                    )
                ]
            # Create a dict of tracks.
            self._tracks = {
                track_id: tracks[track_id] for track_id in playlist_tracks
            }

    def __repr__(self) -> str:
        """Produces a string representation of this playlist.

        Returns:
            Playlist represented as a string.
        """
        # Eventual repr string to return.
        string = "{}{}({}{})"
        # Body of the repr string to fill out with playlist contents.
        body = ""
        # Get the repr recursion depth to determine the degree of indentation.
        depth = len(
            [
                frame for frame in inspect.stack()
                if frame[3] == "__repr__"
                and Path(frame[1]).name == "playlists.py"
            ]
        ) - 1
        # These variables are used to control indentation level.
        extra = 1 if depth else 0
        padding = f"{' ' * 4 * (depth + extra)}"

        # Dunder members aren't represented. Public members (i.e. methods)
        # aren't represented either.
        repr_attrs = {
            key[1:]: value for key, value in self.__dict__.items()
            if not (
                key.startswith(f"_{type(self).__name__}")
                or not key.startswith("_")
                or key == "_parent"
            )
        }

        # Build a representation of this playlist.
        for key, value in repr_attrs.items():
            # Skip representing this playlists's tracks.
            # Defer representation of the playlists attribute until the end.
            if key in ["playlists", "tracks"]:
                continue

            # Represent string values with surrounding double quotes.
            if isinstance(value, str):
                value = f'"{value}"'

            # Append the attribute's name and value to the representation.
            body += f"{key}={value}, "

        # Truncate the final attributes trailing ", ".
        if not repr_attrs["playlists"]:
            body = body[:-2]

        # Now represent the playlist attribute as an indented list of
        # sub-playlists.
        for key, value in repr_attrs.items():
            if key != "playlists" or value is None:
                continue
            body += f"\n{padding + ' ' * 4 * (depth or 1)}{key}=["
            for val in value:
                body += f"\n{' ' * 4 * depth}{repr(val)},"
            # Truncate final comma.
            body = body[:-1]
            body += f"\n{padding + ' ' * 4 * (depth or 1)}],"

        # Truncate final comma.
        if repr_attrs["playlists"]:
            body = body[:-1]

        return string.format(
            padding if depth else "",
            type(self).__name__,
            body,
            f"\n{padding}{' ' * 4 * (depth - 1)}" if self._playlists else "",
        )

    def __str__(self) -> str:
        """Produce a string representation of this playlist.

        Returns:
            Playlist represented as a string.
        """
        return str(self.serialize())

    def get_name(self) -> str:
        """Returns the name of this playlist.

        Returns:
            The name of this playlist.
        """
        return self._Name  # pylint: disable=no-member

    def is_folder(self) -> bool:
        """Returns whether this playlist is a folder or a playlist of tracks.

        Returns:
            Boolean representing whether this is a folder or not.
        """
        return self._Type == "0"  # pylint: disable=no-member

    @classmethod
    def new_playlist(
        cls,
        name: str,
        playlists: Optional[List[RekordboxPlaylist]] = None,
        tracks: Optional[Dict[str, RekordboxTrack]] = None,
    ) -> RekordboxPlaylist:
        """Creates a new playlist.

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
            A new playlist.
        """
        if playlists is None and tracks is None:
            raise RuntimeError(
                "You must provide either a list of RekordboxPlaylists or a "
                "list of RekordboxTracks"
            )
        if playlists is not None and tracks is not None:
            raise RuntimeError(
                "You must not provide both a list of RekordboxPlaylists and a "
                "list of RekordboxTracks"
            )
        playlist_tag = bs4.Tag(
            name="NODE",
            attrs=(
               {"Name": name, "Type": "0", "Count": len(playlists)}
               if playlists else {
                   "Name": name,
                   "Type": "1",
                   "KeyType": "0",
                   "Entries": len(tracks),
               }
            ),
        )
        playlist = RekordboxPlaylist(
            playlist_tag, tracks=tracks, playlist_tracks=(tracks or {}).keys()
        )
        playlist._playlists = playlists

        return playlist

    def serialize(self, *args, **kwargs) -> bs4.element.Tag:
        """Serializes this playlist as a BeautifulSoup NODE Tag.

        Returns:
            BeautifulSoup Tag representing this playlist.
        """
        # BeautifulSoup Tag to populate with attributes of this playlist.
        playlist_tag = bs4.Tag(name="NODE", can_be_empty_element=True)

        # Dunder members aren't serialized. Public members (i.e. methods)
        # aren't serialized either.
        serialize_attrs = {
            key[1:]: value for key, value in self.__dict__.items()
            if not (
                key.startswith(f"_{type(self).__name__}")
                or not key.startswith("_")
                or key == "_parent"
            )
        }

        # Serialize attributes into a NODE Tag.
        for key, value in serialize_attrs.items():
            # Playlists and tracks are serialized as nested Tag objects.
            if key in ["playlists", "tracks"]:
                if not value:
                    continue

                # Iterate and serialize nested playlists.
                if self.is_folder():
                    for val in value:
                        playlist_tag.extend(
                            [bs4.NavigableString("\n"), val.serialize()]
                        )
                # Iterate and serialize tracks.
                else:
                    for val in value.values():
                        playlist_tag.extend(
                            [
                                bs4.NavigableString("\n"),
                                val.serialize(playlist=True),
                            ]
                        )

                # Append a final newline character.
                playlist_tag.append(bs4.NavigableString("\n"))
                continue

            # Otherwise the data is serialized as NODE Tag attributes.
            playlist_tag[key] = value

        # Update the Count or Entries attribute.
        playlist_tag["Count" if self.is_folder() else "Entries"] = str(len(self))

        return playlist_tag

    @classmethod
    def validate(
        cls, original: bs4.element.Tag, serializable: RekordboxPlaylist
    ):
        """Validate the serialized playlist matches the original.

        Args:
            original: BeautifulSoup Tag representing a playlist.
            serializable: Playlist object.
        """
        assert original == serializable.serialize(), (
            "Failed RekordboxPlaylist validation!"
        )
