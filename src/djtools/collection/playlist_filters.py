"""This module contains the PlaylistFilter abstract base class and its\
implementations.

PlaylistFilter subclasses implement an 'is_filter_playlist' method and a
'filter_track' method.

The 'is_filter_playlist' method, when given a 'Playlist', returns true if that
'Playlist' should have its tracks filtered.

The 'filter_track' method, when given a 'Track', returns true if that 'Track'
should remain in the playlist.
"""
from abc import ABC, abstractmethod
import re

from djtools.collection.playlists import Playlist
from djtools.collection.tracks import Track


class PlaylistFilter(ABC):
    "This class defines an interface for filtering tracks from playlists."

    @abstractmethod
    def filter_track(self, track: Track) -> bool:
        """Returns True if this track should remain in the playlist.

        Args:
            track: Track object to apply filter to.

        Returns:
            Whether or not this track should be included in the playlist.
        """

    @abstractmethod
    def is_filter_playlist(self, playlist: Playlist) -> bool:
        """Returns True if this playlist should be filtered.

        Args:
            playlist: Playlist object to potentially filter.

        Returns:
            Whether or not to filter this playlist.
        """


class HipHopFilter(PlaylistFilter):
    'This class filters playlists called "Hip Hop".'

    def filter_track(self, track: Track) -> bool:
        """Returns True if this track should remain in the playlist.

        If the playlist is not underneath a folder called "Bass", then this
        track is filtered out unless it has exclusively "Hip Hop" and "R&B"
        genre tags. If the playlist is underneath a folder called "Bass", then
        this track is filtered out if it does have exclusively "Hip Hop" and
        "R&B" genre tags.

        Args:
            track: Track object to apply filter to.

        Returns:
            Whether or not this track should be included in the playlist.
        """
        pure_hip_hop_with_other_tags = not self._bass_hip_hop and any(
            "r&b" not in x.lower() and "hip hop" not in x.lower()
            for x in track.get_genre_tags()
        )
        bass_hip_hop_without_other_tags = self._bass_hip_hop and all(
            "r&b" in x.lower() or "hip hop" in x.lower()
            for x in track.get_genre_tags()
        )
        if pure_hip_hop_with_other_tags or bass_hip_hop_without_other_tags:
            return False

        return True


    def is_filter_playlist(self, playlist: Playlist) -> bool:
        """Returns True if this playlist's name is "Hip Hop".

        Args:
            playlist: Playlist object to potentially filter.

        Returns:
            Whether or not to filter this playlist.
        """
        if not playlist.get_name() == "Hip Hop":
            return False

        self._bass_hip_hop = False  #pylint: disable=attribute-defined-outside-init
        parent = playlist.get_parent()
        while parent:
            if parent.get_name() == "Bass":
                self._bass_hip_hop = True  #pylint: disable=attribute-defined-outside-init
            parent = parent.get_parent()

        return True


class MinimalDeepTechFilter(PlaylistFilter):
    'This class filters playlists called "Minimal Deep Tech".'

    def filter_track(self, track: Track) -> bool:
        """Returns True if this track should remain in the playlist.

        If the playlist is not underneath a folder called "Techno", then this
        track is filtered out if the genre tag preceding "Minimal Deep Tech" is
        "Techno". If the playlist is underneath a folder called "Techno", then
        this track is filtered out if the genre tag preceding
        "Minimal Deep Tech" is not "Techno".

        Args:
            track: Track object to apply filter to.

        Returns:
            Whether or not this track should be included in the playlist.
        """
        house_exp = re.compile(r".*house.*")
        techno_exp = re.compile(r".*techno.*")
        house_tag = techno_tag = False
        for tag in track.get_genre_tags():
            if re.search(house_exp, tag.lower()):
                house_tag = True
            if re.search(techno_exp, tag.lower()):
                techno_tag = True
        if (
            (self._techno and not techno_tag) or
            (self._house and not house_tag)
        ):
            return False

        return True

    def is_filter_playlist(self, playlist: Playlist) -> bool:
        """Returns True if this playlist's name is "Minimal Deep Tech".

        Args:
            playlist: Playlist object to potentially filter.

        Returns:
            Whether or not to filter this playlist.
        """
        if not playlist.get_name() == "Minimal Deep Tech":
            return False

        self._techno = False  #pylint: disable=attribute-defined-outside-init
        self._house = False  #pylint: disable=attribute-defined-outside-init
        parent = playlist.get_parent()
        while parent:
            if parent.get_name() == "Techno":
                self._techno = True  #pylint: disable=attribute-defined-outside-init
            if parent.get_name() == "House":
                self._house = True  #pylint: disable=attribute-defined-outside-init
            parent = parent.get_parent()

        return True
