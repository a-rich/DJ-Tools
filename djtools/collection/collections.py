"""This module contains classes for collections of different DJ software
platforms.

Collection is an abstract base class which defines the interface expected of a
collection; namely methods for (de)serialization to/from the representation
recognized by the DJ software for which Collection is being sub-classed.

RekordboxCollection is an implementation of Collection which operates on the
XML format that Rekordbox exports. The CustomSubstitution and
UnsortedAttributes classes are helpers for serializing a RekordboxCollection.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from copy import copy
from pathlib import Path
import re
from typing import Dict, Iterator, List, Optional, Tuple, Union

import bs4
from bs4 import BeautifulSoup
from bs4.dammit import EntitySubstitution
from bs4.formatter import XMLFormatter

from djtools.collection.playlists import Playlist, RekordboxPlaylist
from djtools.collection.tracks import RekordboxTrack, Track


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

    def get_playlists(
        self, name: Optional[str] = None
    ) -> Union[Playlist, List[Playlist]]:
        """Returns Playlists with a matching name.

        If no playlist name is provided, then the root playlist is returned.

        Args:
            name: Name of the Playlists to return.

        Returns:
            The Playlists with the same name.
        """
        if not name:
            return self._playlists  # pylint:disable=no-member

        playlists = []
        for playlist in self._playlists:  # pylint:disable=no-member
            if playlist.get_name() == name:
                playlists.append(playlist)
            if playlist.is_folder():
                for playlist in playlist:
                    playlists.extend(playlist.get_playlists(name))

        return [playlist for playlist in playlists if playlist is not None]

    def get_tracks(self) -> Dict[str, Track]:
        """Returns the tracks in the collection.

        Returns:
            Dict of tracks.
        """
        return self._tracks

    @abstractmethod
    def reset_playlists(self):
        """Resets the Playlists in the Collection to be empty."""

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


class RekordboxCollection(Collection):
    "Collection implementation for usage with Rekordbox."

    def __init__(self, path: Path):
        """Deserializes a Collection from an XML file.

        Args:
            path: Path to a serialized collection.
        """
        self._path = path

        # Parse the XML as a BeautifulSoup document.
        with open(self._path, mode="r", encoding="utf-8") as _file:
            self._collection = BeautifulSoup(_file.read(), "xml")

        # Create a dict of tracks.
        self._tracks = {
            track["TrackID"]: RekordboxTrack(track)
            for track in self._collection.find_all("TRACK")
            if track.get("Location")
        }

        # Instantiate the Playlist(s) in this collection.
        self._playlists = RekordboxPlaylist(
            self._collection.find("NODE", {"Name": "ROOT", "Type": "0"}),
            tracks=self._tracks,
        )

    def __repr__(self) -> str:
        """Produce a string representation of this Collection.

        Returns:
            Collection represented as a string.
        """
        # Eventual repr string to return.
        string = "{}({}\n)"
        # Body to the repr string to fill out with Collection content.
        body =  ""

        # Dunder methods aren't represented. Public members (i.e methods)
        # aren't represented either.
        repr_attrs = {
            key[1:]: value for key, value in self.__dict__.items()
            if not(
                key.startswith(f"_{type(self).__name__}")
                or not key.startswith("_")
                or key == "_collection"
            )
        }

        # Build a representation of this Collection.
        for key, value in repr_attrs.items():
            # Skip representing this collection's playlists and tracks.
            # Defer representation of the playlists attribute until the end.
            if key in ["playlists", "tracks"]:
                continue

            # Represent string values with surrounding double quotes.
            if isinstance(value, (Path, str)):
                value=  f'"{value}"'

            # Append the attribute's name and value to the representation.
            body += f"\n{' ' * 4}{key}={value},"

        # Now represent the playlists and tracks attributes as an indented list
        # of playlists and number of tracks, respectively.
        for key, value in repr_attrs.items():
            if key not in ["playlists", "tracks"]:
                continue
            if isinstance(value, dict):
                body += f"\n{' ' * 4}{key}={len(value)},"
            else:
                # TODO(a-rich): split and join with extra indents.
                body += f"\n{' ' * 4}{key}=["
                playlists = f"\n{' ' * 8}".join(repr(value).split("\n"))
                body += f"\n{' ' * 8}{playlists}"
                body += f"\n{' ' * 4}]"

        return string.format(type(self).__name__, body)

    def __str__(self) -> str:
        """Produces a string representation of this Collection.

        Returns:
            Collection represented as a string.
        """
        return str(self.serialize())

    def reset_playlists(self):
        """Resets the Playlists in the Collection to be empty."""
        root = self._collection.find("NODE", {"Name": "ROOT", "Type": "0"})
        for child in list(root.children):
            child.extract()
        self._playlists = RekordboxPlaylist(root, tracks=self._tracks)

    def serialize(
        self, *args, new_path: Optional[Path] = None, **kwargs
    ) -> Path:
        """Serializes this Collection as an XML file.

        Args:
            new_path: Path to output serialized collection to.

        Returns:
            Path to the serialized collection XML file.
        """
        # BeautifulSoup document.
        doc = BeautifulSoup("", features="xml")

        # Tag that contains all the playlist data.
        root_tag_name = "DJ_PLAYLISTS"

        # Retrieve this root tag from the existing document, rather than
        # building it from scratch, in case the attributes ever change.
        root_tag = bs4.Tag(
            name=root_tag_name,
            attrs=self._collection.find(root_tag_name).attrs,
        )

        # Similarly, we want to reference the existing attribute data on the
        # product Tag.
        root_tag.extend(
            [bs4.NavigableString("\n"), copy(self._collection.find("PRODUCT"))]
        )

        # Build the collection Tag and serialize each track into it before
        # adding the collection Tag to the root.
        collection_tag = bs4.Tag(
            name="COLLECTION", attrs={"Entries": str(len(self._tracks))}
        )
        for track in self._tracks.values():
            collection_tag.extend(
                [bs4.NavigableString("\n"), track.serialize()]
            )
        collection_tag.append(bs4.NavigableString("\n"))
        root_tag.extend([bs4.NavigableString("\n"), collection_tag])

        # Build the playlists Tag and serialize each Playlist into it before
        # adding the playlist Tag to the root.
        playlists_tag = bs4.Tag(name="PLAYLISTS")
        playlists_root_tag = bs4.Tag(
            name="NODE",
            attrs={"Type": "0", "Name": "ROOT", "Count": len(self._playlists)},
        )
        for playlist in self._playlists:
            playlists_root_tag.extend(
                [bs4.NavigableString("\n"), playlist.serialize()]
            )
        playlists_root_tag.append(bs4.NavigableString("\n"))
        playlists_tag.extend(
            [
                bs4.NavigableString("\n"),
                playlists_root_tag,
                bs4.NavigableString("\n"),
            ]
        )
        root_tag.extend(
            [
                bs4.NavigableString("\n"),
                playlists_tag,
                bs4.NavigableString("\n"),
            ]
        )
        doc.append(root_tag)

        # If no new path is provided, use the original but prefix the file name
        # with "auto_".
        if not new_path:
            new_path = self._path.parent / f"auto_{self._path.name}"

        # Write the serialized Collection to a new file.
        with open(new_path, mode="w", encoding="utf-8") as _file:
            _file.write(
                doc.prettify(
                    # UnsortedAttributes formatter ensures attributes are
                    # serialized in the same order as the original XML file.
                    formatter=UnsortedAttributes(
                        indent=2,
                        # CustomSubstitution is used to substitute an expanded
                        # character set in the serialized XML file.
                        entity_substitution=CustomSubstitution.substitute_xml,
                    )
                )
            )

        return new_path

    @classmethod
    def validate(cls, input_xml: Path, output_xml: Path):
        """Validate the serialized Collection matches the original.

        Args:
            input_xml: Path to an XML containing the original collection.
            output_xml: Path to an XML containing the serialized collection.

        Raises:
            AssertionError: A serialized Collection must exactly match the
                original XML used to deserialize from.
        """
        # Read the original and serialized collection XML files as
        # strings.
        with open(input_xml, mode="r", encoding="utf-8") as _file:
            input_xml_string = _file.read()
        with open(output_xml, mode="r", encoding="utf-8") as _file:
            output_xml_string = _file.read()

        # Rekordbox capitalizes "UTF-8" in the file declaration while
        # BeautifulSoup does not.
        xml_declaration = input_xml_string[:38]
        output_xml_string = xml_declaration + output_xml_string[38:]

        # Replace multiple occurrences of whitespace with a single whitespace.
        whitespace = re.compile(r"/\s{2,}/g")
        input_xml_string = re.sub(whitespace, input_xml_string, " ")
        output_xml_string = re.sub(whitespace, output_xml_string, " ")

        assert input_xml_string == output_xml_string, (
            "Failed RekordboxCollection validation!"
        )


class CustomSubstitution(EntitySubstitution):
    "Helper class to serialize Tags with proper character substitution."

    # Regular expression to match brackets, ampersands, and quotes.
    AMPERSAND_OR_BRACKET_OR_QUOTES = re.compile("([<>&'\"])")

    @classmethod
    def substitute_xml(
        cls, value: str, make_quoted_attribute: bool = False
    ) -> str:
        """Substitute XML entities for special XML characters.

        Args:
            value: A string to be substituted.
            make_quoted_attribute: If True, then the string will be quoted.

        Returns:
            String value with it's characters substituted.
        """
        # Escape angle brackets, ampersands, single quotes, and double quotes.
        value = cls.AMPERSAND_OR_BRACKET_OR_QUOTES.sub(
            cls._substitute_xml_entity, value)

        if make_quoted_attribute:
            value = cls.quoted_attribute_value(value)  # pragma: no cover

        return value


class UnsortedAttributes(XMLFormatter):
    "Helper class to serialize Tag attributes in their original order."

    def attributes(self, tag: bs4.element.Tag) -> Iterator[Tuple[str, str]]:
        """Generator that returns a Tag's attributes as key / value pairs.

        Args:
            tag: Tag from a Collection.

        Yields:
            Tuple containing a key / value representing an attribute.
        """
        for key, value in tag.attrs.items():
            yield key, value
