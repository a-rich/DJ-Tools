"""This module contains the base class for tracks of different DJ software
platforms.

Track is an abstract base class which defines the interface expected of a
track; namely methods for (de)serialization to/from the representation
recognized by the DJ software for which Track is being sub-classed.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List


# pylint: disable=no-member,duplicate-code


class Track(ABC):
    "Abstract base class for a track."

    @abstractmethod
    def __init__(self, *args, **kwargs):
        "Deserializes a track from the native format of a DJ software."

    @abstractmethod
    def get_artists(self) -> str:
        """Gets the track artists.

        Returns:
            A string representing the track's artists.
        """

    @abstractmethod
    def get_bpm(self) -> float:
        """Gets the track BPM.

        Returns:
            A float representing BPM.
        """

    @abstractmethod
    def get_comments(self) -> str:
        """Gets the track comments.

        Returns:
            A string representing the track's comments.
        """

    @abstractmethod
    def get_date_added(self) -> str:
        """Gets the track's date added.

        Returns:
            A datetime representing the track's date added.
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
    def get_key(self) -> Any:
        """Gets the track key.

        Returns:
            The key of this track.
        """

    @abstractmethod
    def get_label(self) -> Any:
        """Gets the track label.

        Returns:
            The label of this track.
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
    def get_tags(self) -> List[str]:
        """Gets the tags of the track.

        Returns:
            A set of the track's tags.
        """

    @abstractmethod
    def get_year(self) -> str:
        """Gets the year of the track.

        Returns:
            The year of the track.
        """

    @abstractmethod
    def serialize(self, *args, **kwargs) -> Any:
        """Serializes a track into the native format of a DJ software.

        Returns:
            A serialized track of the same type used to initialize Track.
        """

    @abstractmethod
    def set_location(self, location: Path):
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
