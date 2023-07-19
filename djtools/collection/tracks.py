"""This module contains classes for tracks of different DJ software platforms.

Track is an abstract base class which defines the interface expected of a
track; namely methods for (de)serialization to/from the representation
recognized by the DJ software for which Track is being sub-classed.

RekordboxTrack is an implementation of Track which operates on the XML format
that Rekordbox exports.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
import os
from pathlib import Path
import re
from typing import Any, List, Union, Set
from urllib.parse import quote, unquote

import bs4


class Track(ABC):
    "Abstract base class for a track."

    @abstractmethod
    def __init__(self, *args, **kwargs):
        "Deserializes a track from the native format of a DJ software."

    @abstractmethod
    def get_bpm(self) -> float:
        """Gets the track BPM.

        Returns:
            A float representing BPM.
        """

    @abstractmethod
    def get_genre_tags(self) -> List[str]:
        """Gets the genre tags of the track.

        Returns:
            A list of the track's genre tags.            
        """

    @abstractmethod
    def get_id(self) -> Any:
        """Gets the track ID.

        Returns:
            The ID of this track.
        """

    @abstractmethod
    def get_location(self) -> Path:
        """Gets the location of the track.

        Returns:
            The Path for the location of the track.
        """

    @abstractmethod
    def get_rating(self) -> int:
        """Gets the rating of the track.

        Returns:
            The rating of the track.
        """

    @abstractmethod
    def get_tags(self) -> Set[str]:
        """Gets the tags of the track.

        Returns:
            A set of the track's tags.
        """

    @abstractmethod
    def serialize(self, *args, **kwargs) -> Any:
        """Serializes a track into the native format of a DJ software.

        Returns:
            A serialized track of the same type used to initialize Track.
        """

    @abstractmethod
    def set_location(self, location: Union[Path, str]):
        """Sets the path of the track to location.

        Args:
            location: New location of the track.
        """

    @abstractmethod
    def set_track_number(self, number: int):
        """Sets the track number of a track.

        Args:
            number: Number to set for TrackNumber.
        """


class RekordboxTrack(Track):
    "Track implementation for usage with Rekordbox."

    def __init__(self, track: bs4.element.Tag):
        """Deserialize a track from a BeautifulSoup TRACK Tag.

        Args:
            track: BeautifulSoup Tag representing a track.
        """
        # Prefix of the path to the audio file corresponding to this track.
        self.__location_prefix = "file://localhost"

        # Set class attributes from TRACK Tag attributes.
        for key, value in track.attrs.items():
            if key in [
                "BitRate",
                "DiscNumber",
                "PlayCount",
                "SampleRate",
                "Size",
                "TotalTime",
                "TrackNumber",
            ]:
                value = int(value)
            if key == "AverageBpm":
                value = float(value)
            if key == "DateAdded":
                # We need to keep the original date added string because
                # Rekordbox doesn't format date strings consistently i.e.
                # ensuring perfect serialization symmetry is not possible
                # without this.
                self.__original_date_added = value
                value = datetime.strptime(value, "%Y-%m-%d")
            if key == "Genre":
                value = [x.strip() for x in value.split("/")]
            if key == "Location":
                value = Path(unquote(value).split(self.__location_prefix)[-1])
            if key == "Rating":
                value = {
                    "0": 0, "51": 1, "102": 2, "153": 3, "204": 4, "255": 5
                }.get(value)
            setattr(self, f"_{key}", value)

        # Parse MyTag data from Comments attribute.
        my_tags = re.search(r"(?<=\/\*).*(?=\*\/)", self._Comments)  # pylint: disable=no-member
        self._MyTags = (  # pylint: disable=invalid-name
            [x.strip() for x in my_tags.group().split("/")] if my_tags else []
        )

        # Merge Genre and MyTag data into a new attribute.
        self._Tags = set(self._Genre + self._MyTags)  # pylint: disable=no-member, invalid-name

        # Parse TEMPO Tags as the beat grid attribute.
        self._beat_grid = track.find_all("TEMPO")
        if self._beat_grid:
            self._beat_grid = [point.attrs for point in self._beat_grid]

        # Parse POSITION_MARK Tags as the hot cues attribute.
        self._hot_cues = track.find_all("POSITION_MARK")
        if self._hot_cues:
            self._hot_cues = [hot_cue.attrs for hot_cue in self._hot_cues]

    def __repr__(self) -> str:
        """Produces a string representation of this track.

        Returns:
            Track represented as a string.
        """
        # Enforce a maximum width for a Track representation.
        max_width = 79
        # Eventual repr string to return.
        string = "{}(\n{}\n)"
        # Body of the repr string to fill out with track contents.
        body = ' ' * 4

        # Dunder members aren't represented. Public members (i.e. methods)
        # aren't represented either.  # pylint: disable=duplicate-code
        repr_attrs = {
            key[1:]: value for key, value in self.__dict__.items()
            if not (
                key.startswith(f"_{type(self).__name__}")
                or not key.startswith("_")
            )
        }

        # Build a representation of this track.
        for key, value in repr_attrs.items():
            # Prettify output by enforcing `max_width`.
            if len(body.split("\n", maxsplit=-1)[-1]) > max_width:
                body += f"\n{' ' * 4}"

            # Rather than display each beat grid or hot cue attribute, simply
            # represent as the number of those attributes.
            if key in ["beat_grid", "hot_cues"]:
                value = len(value)

            # Represent string values with surrounding double quotes.
            if isinstance(value, str):
                value = f'"{value}"'

            # Truncate the HH:MM:SS part of the datetime.
            if isinstance(value, datetime):
                value = f'"{value.strftime("%Y-%m-%d")}"'

            # Append the attribute's name and value to the representation.
            body += f"{key}={value}, "

        # Truncate final comma and space.
        body = body[:-2]

        return string.format(type(self).__name__, body)

    def __str__(self) -> str:
        """Produces a string representation of this track.

        Returns:
            Track represented as a string.
        """
        return str(self.serialize())

    def get_bpm(self) -> float:
        """Gets the track BPM.

        Returns:
            A float representing BPM.
        """
        return self._AverageBpm  # pylint: disable=no-member

    def get_genre_tags(self) -> List[str]:
        """Gets the genre tags of the track.

        Returns:
            A list of the track's genre tags.            
        """
        return self._Genre  # pylint: disable=no-member

    def get_id(self) -> str:
        """Get the track ID.

        Returns:
            The ID of this track.
        """
        return self._TrackID  # pylint: disable=no-member

    def get_location(self) -> Path:
        """Gets the location of the track.

        Returns:
            The Path for the location of the track.
        """
        return self._Location

    def get_rating(self) -> int:
        """Gets the rating of the track.

        Returns:
            The rating of the track.
        """
        return self._Rating  # pylint: disable=no-member

    def get_tags(self) -> Set[str]:
        """Gets the tags of the track.

        Returns:
            A set of the track's tags.
        """
        return self._Tags

    def serialize(
        self, *args, playlist: bool = False, **kwargs
    ) -> bs4.element.Tag:
        """Serializes this track as a BeautifulSoup TRACK Tag.

        Args:
            playlist: Whether or not to serialize this track as a member of a
                playlist.
        
        Raises:
            ValueError: The DateAdded attribute must serialize into its
                original format.

        Returns:
            BeautifulSoup Tag representing this track.
        """
        # BeautifulSoup Tag to populate with attributes of this track.
        track_tag = bs4.Tag(name="TRACK", can_be_empty_element=True)

        # TRACK Tags in playlists are serialized differently from top-level
        # TRACK Tags.
        if playlist:
            track_tag["Key"] = self.get_id()

            return track_tag

        # Dunder members aren't serialized. Public members (i.e. methods)
        # aren't serialized either.
        serialize_attrs = {
            key[1:]: value for key, value in self.__dict__.items()
            if not (
                key.startswith(f"_{type(self).__name__}")
                or not key.startswith("_")  # pylint: disable=duplicate-code
                or key in ["_MyTags", "_Tags"]
            )
        }

        # Serialize attributes into a TRACK Tag.
        for key, value in serialize_attrs.items():
            # Beat grid and hot cue data is serialized as TEMPO and
            # POSITION_MARK Tags, respectively.
            if key in ["beat_grid", "hot_cues"]:
                for val in value:
                    tag = bs4.Tag(
                        name="POSITION_MARK" if key == "hot_cues" else "TEMPO",
                        can_be_empty_element=True,
                    )
                    tag.attrs = val
                    track_tag.extend([bs4.NavigableString("\n"), tag])
                continue

            # Cast integers back into a string.
            if key in [
                "BitRate",
                "DiscNumber",
                "PlayCount",
                "SampleRate",
                "Size",
                "TotalTime",
                "TrackNumber",
            ]:
                value = str(value)

            # Increase BPM precision to make serialization 100% symmetrical.
            if key == "AverageBpm":
                value = f"{value:0,.2f}"

            # Truncate the HH:MM:SS part of the datetime.
            if isinstance(value, datetime):
                # Rekordbox doesn't consistently format dates with or without
                # leading zeros on the month and day portion of the date
                # string, so we have to try all three of these formats to see
                # if the resulting formatting matches the original one.
                date_formats = [
                    "%Y-%m-%d",
                    ("%Y-%-m-%d" if os.name == "posix" else "%Y-%#m-%d"),
                    ("%Y-%-m-%-d" if os.name == "posix" else "%Y-%#m-%#d"),
                ]
                for date_format in date_formats:
                    attempt = value.strftime(date_format)
                    if attempt == self.__original_date_added:
                        break
                value = attempt

                if value != self.__original_date_added:
                    raise ValueError(  # pragma: no cover
                        f"Failed to serialize the datetime {value} into its "
                        f"original format {self.__original_date_added}"
                    )

            # Re-join genre tags with forward slashes.
            if key == "Genre":
                value = " / ".join(value)

            # Re-insert the location prefix and quote the path.
            if key == "Location":
                track_path = quote(value.as_posix(), safe="/,()!+=#;$:")
                slash_char = "/" if not track_path.startswith("/") else ""
                value = f"{self.__location_prefix}{slash_char}{track_path}"
                value = re.sub(
                    r'%[0-9A-Z]{2}', lambda x: x.group(0).lower(), value 
                )

            # Reverse the rating value to the range recognized by Rekordbox.
            if key == "Rating":
                value = {
                    0: "0", 1: "51", 2: "102", 3: "153", 4: "204", 5: "255"
                }.get(value)

            # Otherwise the data is serialized as TRACK Tag attributes.
            track_tag[key] = value

        # If this TRACK Tag has children, append a final newline character.
        if len(track_tag) > 1:
            track_tag.append(bs4.NavigableString("\n"))

        return track_tag

    def set_location(self, location: Union[Path, str]):
        """Sets the path of the track to location.

        Args:
            location: New location of the track.
        """
        self._Location = Path(location)  # pylint: disable=attribute-defined-outside-init,invalid-name

    def set_track_number(self, number: int):
        """Sets the track number of a track.

        Args:
            number: Number to set for TrackNumber.
        """
        self._TrackNumber = number  # pylint: disable=invalid-name,attribute-defined-outside-init

    @classmethod
    def validate(cls, original: bs4.element.Tag, serializable: RekordboxTrack):
        """Validate the serialized track matches the original. 

        Args:
            original: BeautifulSoup Tag representing a track.
            serializable: Track object.

        Raises:
            AssertionError: Serialized Collection must match the original.
        """
        assert original == serializable.serialize(), (
            "Failed RekordboxTrack validation!"
        )
