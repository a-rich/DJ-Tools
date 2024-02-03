"""This module contains the class for RekordbxPlaylist.

RekordboxPlaylist is an implementation of Playlist which operates on the XML
format that Rekordbox exports.
"""

from __future__ import annotations
import inspect
from pathlib import Path
from typing import Dict, List, Optional

import bs4

from djtools.collection.base_playlist import Playlist
from djtools.collection.rekordbox_track import RekordboxTrack


# pylint: disable=duplicate-code


class RekordboxPlaylist(Playlist):
    "Playlist implementation for usage with Rekordbox."

    def __init__(
        self,
        playlist: bs4.element.Tag,
        tracks: Dict[str, RekordboxTrack] = None,
        playlist_tracks: Optional[Dict[str, RekordboxTrack]] = None,
        parent: Optional[RekordboxPlaylist] = None,
    ):
        """Deserialize a Playlist from a BeautifulSoup NODE Tag.

        Args:
            playlist: BeautifulSoup Tag representing a playlist.
            tracks: All the tracks in this collection.
            playlist_tracks: Tracks to set when initializing with new_playlist.
            parent: The folder this playlist is in.
        """
        super().__init__()
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
                    track.get("Key")
                    for track in filter(
                        lambda x: isinstance(x, bs4.element.Tag),
                        playlist.children,
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
        depth = (
            len(
                [
                    frame
                    for frame in inspect.stack()
                    if frame[3] == "__repr__"
                    and Path(frame[1]).name == "rekordbox_playlist.py"
                ]
            )
            - 1
        )
        # These variables are used to control indentation level.
        extra = 1 if depth else 0
        padding = f"{' ' * 4 * (depth + extra)}"

        # Dunder members aren't represented. Public members (i.e. methods)
        # aren't represented either.
        repr_attrs = {
            key[1:]: value
            for key, value in self.__dict__.items()
            if not (
                key.startswith(f"_{type(self).__name__}")
                or not key.startswith("_")
                or key == "_parent"
            )
        }

        # Build a representation of this playlist.
        for key, value in repr_attrs.items():
            # Skip representing this playlist's tracks.
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
        else:
            body = body[:-1]

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
                if playlists is not None
                else {
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
            key[1:]: value
            for key, value in self.__dict__.items()
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
        playlist_tag["Count" if self.is_folder() else "Entries"] = str(
            len(self)
        )

        return playlist_tag
