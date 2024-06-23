"""This module contains the PlaylistFilter abstract base class and its
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
from typing import List, Optional

from djtools.collection.base_playlist import Playlist
from djtools.collection.base_track import Track


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
        self._bass_hip_hop = (  # pylint: disable=attribute-defined-outside-init
            False
        )

        if not playlist.get_name() == "Hip Hop":
            return False

        parent = playlist.get_parent()
        while parent:
            if parent.get_name() == "Bass":
                self._bass_hip_hop = (  # pylint: disable=attribute-defined-outside-init
                    True
                )
                break
            parent = parent.get_parent()

        return True


class MinimalDeepTechFilter(PlaylistFilter):
    'This class filters playlists called "Minimal Deep Tech".'

    def filter_track(self, track: Track) -> bool:
        """Returns True if this track should remain in the playlist.

        If the playlist is not underneath a folder called "Techno", then this
        track is filtered out if there's another genre tag containing "Techno".
        If the playlist is underneath a folder called "Techno", then
        this track is filtered out if there's no other genre tag containing
        "Techno".

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
        if (self._techno and not techno_tag) or (
            self._house and not house_tag
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
        self._techno = False  # pylint: disable=attribute-defined-outside-init
        self._house = False  # pylint: disable=attribute-defined-outside-init

        if not playlist.get_name() == "Minimal Deep Tech":
            return False

        parent = playlist.get_parent()
        while parent:
            if parent.get_name() == "Techno":
                self._techno = (  # pylint: disable=attribute-defined-outside-init
                    True
                )
            if parent.get_name() == "House":
                self._house = (  # pylint: disable=attribute-defined-outside-init
                    True
                )
            parent = parent.get_parent()

        return self._techno or self._house


class ComplexTrackFilter(PlaylistFilter):
    """This class filters "complex" playlists.

    This PlaylistFilter looks for playlists with "complex" in their name or in
    the name of a parent playlist. When found, tracks contained in the playlist
    must have no less than 'min_tags_for_complex_track' in order to remain in
    the playlist.
    """

    def __init__(
        self,
        min_tags_for_complex_track: Optional[int] = 3,
        exclude_tags: Optional[List[str]] = None,
    ):
        """Constructor.

        Args:
            min_tags_for_complex_track: Maximum number of non-genre tags before
                a track is no longer considered "complex".
            exclude_tags: Tags to ignore when determining the number of
                non-genre tags.
        """
        super().__init__()
        self._min_tags_for_complex_track = min_tags_for_complex_track
        if exclude_tags is None:
            exclude_tags = [
                "DELETE",
                "Flute",
                "Guitar",
                "Horn",
                "Piano",
                "Scratch",
                "Strings",
                "Vocal",
            ]
        self._exclude_tags = set(exclude_tags)

    def filter_track(self, track: Track) -> bool:
        """Returns True if this track should remain in the playlist.

        Args:
            track: Track object to apply filter to.

        Returns:
            Whether or not this track should be included in the playlist.
        """
        other_tags = (
            set(track.get_tags())
            .difference(set(track.get_genre_tags()))
            .difference(self._exclude_tags)
        )

        return (
            other_tags and len(other_tags) >= self._min_tags_for_complex_track
        )

    def is_filter_playlist(self, playlist: Playlist) -> bool:
        """Returns True if this playlist should be filtered.

        Args:
            playlist: Playlist object to potentially filter.

        Returns:
            Whether or not to filter this playlist.
        """
        playlist_exp = re.compile(r".*complex.*")
        if re.search(playlist_exp, playlist.get_name().lower()):
            return True

        parent = playlist.get_parent()
        while parent:
            if re.search(playlist_exp, parent.get_name().lower()):
                return True
            parent = parent.get_parent()

        return False


class TransitionTrackFilter(PlaylistFilter):
    """This class filters "transition" playlists.

    This PlaylistFilter looks for playlists with "transition" in their name or in
    the name of a parent playlist. When found, tracks contained in the playlist
    must have a square bracket enclosed set of transition tokens (forward-slash
    delimited list of floats, for BPMs, or otherwise, for genres).
    """

    def __init__(self, separator: Optional[str] = "/"):
        """Constructor.

        Args:
            separator: Character used to separate transition tokens.
        """
        super().__init__()
        self._separator = separator
        self._playlist_type = None

    def filter_track(self, track: Track) -> bool:
        """Returns True if this track should remain in the playlist.

        Matches square bracket enclosed tokens representing transitions for
        supported playlist types.

        Args:
            track: Track object to apply filter to.

        Returns:
            Whether or not this track should be included in the playlist.
        """
        comments = track.get_comments()
        transition_exp = re.compile(r"\[([^]]+)\]")
        transition_tokens_match_playlist_type = False
        for match in re.findall(transition_exp, comments):
            try:
                _ = [
                    float(token.strip())
                    for token in match.split(self._separator)
                ]
                if self._playlist_type == "tempo":
                    transition_tokens_match_playlist_type = True
            except ValueError:
                if self._playlist_type == "genre":
                    transition_tokens_match_playlist_type = True

        return transition_tokens_match_playlist_type

    def is_filter_playlist(self, playlist: Playlist) -> bool:
        """Returns True if this playlist should be filtered.

        Identifies playlists with a supported transition playlist type in its
        name while also having a parent playlist with "transition" in its name.

        Args:
            playlist: Playlist object to potentially filter.

        Returns:
            Whether or not to filter this playlist.
        """
        is_transition_playlist = False

        # Check if the given playlist has a substring of "transition".
        playlist_exp = re.compile(r".*transition.*")
        if re.search(playlist_exp, playlist.get_name().lower()):
            is_transition_playlist = True

        # Search parents' names for "transition" substring.
        parent = playlist.get_parent()
        while not is_transition_playlist and parent:
            if re.search(playlist_exp, parent.get_name().lower()):
                is_transition_playlist = True
            parent = parent.get_parent()

        if not is_transition_playlist:
            return False

        # Check if the given playlist contains one, and only one, of the
        # supported transition playlist types.
        self._playlist_type = None
        playlist_type_exprs = {
            "genre": re.compile(r".*genre.*"),
            "tempo": re.compile(r".*tempo.*"),
        }
        for playlist_type, exp in playlist_type_exprs.items():
            if not re.search(exp, playlist.get_name().lower()):
                continue
            if self._playlist_type:
                raise ValueError(
                    f'"{playlist.get_name()}" matches multiple playlist types:'
                    f" {self._playlist_type}, {playlist_type}"
                )
            self._playlist_type = playlist_type

        return bool(self._playlist_type)
