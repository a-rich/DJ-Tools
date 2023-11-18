"""Testing for the playlist_filters module."""
from unittest import mock

import pytest

from djtools.collection.helpers import PLATFORM_REGISTRY
from djtools.collection.playlist_filters import (
    ComplexTrackFilter,
    HipHopFilter,
    MinimalDeepTechFilter,
    TransitionTrackFilter,
)
from djtools.collection.tracks import RekordboxTrack


@pytest.mark.parametrize(
    "bass_hip_hop,genre_tags,expected",
    [
        (True, ["Hip Hop", "R&B"], False),
        (True, ["Hip Hop", "Trap"], True),
        (False, ["Hip Hop", "R&B"], True),
        (False, ["Hip Hop", "Trap"], False),
    ],
)
def test_hiphopfilter(bass_hip_hop, genre_tags, expected, rekordbox_track):
    """Test for the HipHopFilter class."""
    track_filter = HipHopFilter()
    with mock.patch.object(
        track_filter, "_bass_hip_hop", bass_hip_hop, create=True
    ), mock.patch.object(
        RekordboxTrack, "get_genre_tags", lambda x: genre_tags
    ):
        result = track_filter.filter_track(rekordbox_track)
        assert result == expected


@pytest.mark.parametrize(
    "techno,genre_tags,expected",
    [
        (True, ["Techno", "Minimal Deep Tech"], True),
        (True, ["House", "Minimal Deep Tech"], False),
        (False, ["Techno", "Minimal Deep Tech"], False),
        (False, ["House", "Minimal Deep Tech"], True),
    ],
)
def test_minimaldeeptechfilter(techno, genre_tags, expected, rekordbox_track):
    """Test for the HipHopFilter class."""
    track_filter = MinimalDeepTechFilter()
    with mock.patch.object(
        track_filter, "_techno", techno, create=True
    ), mock.patch.object(
        track_filter, "_house", not techno, create=True
    ), mock.patch.object(
        RekordboxTrack, "get_genre_tags", lambda x: genre_tags
    ):
        result = track_filter.filter_track(rekordbox_track)
        assert result == expected


@pytest.mark.parametrize(
    "parent_playlist_name,playlist_name,expected",
    [
        ("something", "complex", True),
        ("complex", "irrelevant", True),
        ("irrelevant", "something", False),
    ],
)
def test_complextrackfilter_skips_irrelevant_playlists(
    parent_playlist_name,
    playlist_name,
    expected,
):
    """Test for the ComplexTrackFilter class."""
    track_filter = ComplexTrackFilter()
    playlist_class = next(iter(PLATFORM_REGISTRY.values()))["playlist"]
    playlist = playlist_class.new_playlist(playlist_name, tracks={})
    parent_playlist = playlist_class.new_playlist(
        parent_playlist_name, playlists=[playlist]
    )
    playlist.set_parent(parent_playlist)
    result = track_filter.is_filter_playlist(playlist)
    assert result == expected


@pytest.mark.parametrize(
    "max_tags,tags,expected",
    [
        (1, set(["Tag"]), True),
        (2, set(["Tag"]), False),
        (2, set(["Tag", "Another Tag"]), True),
        (3, set(["Tag", "Another Tag"]), False),
        (3, set(["Tag", "Another Tag", "Last Tag"]), True),
    ],
)
def test_complextrackfilter_filters_tracks(
    max_tags, tags, expected, rekordbox_track
):
    """Test for the ComplexTrackFilter class."""
    track_filter = ComplexTrackFilter(max_tags)
    playlist_class = next(iter(PLATFORM_REGISTRY.values()))["playlist"]
    rekordbox_track._Tags = tags  # pylint: disable=protected-access
    playlist = playlist_class.new_playlist(
        "genres", tracks={rekordbox_track.get_id(): rekordbox_track}
    )
    root_playlist = playlist_class.new_playlist(
        "complex", playlists=[playlist]
    )
    playlist.set_parent(root_playlist)
    result = track_filter.filter_track(rekordbox_track)
    assert result == expected


@pytest.mark.parametrize(
    "parent_playlist_name,playlist_name,expected",
    [
        ("transitions", "genres", True),
        ("transitions", "tempos", True),
        ("irrelevant", "transitions", False),
        ("irrelevant", "genres", False),
        ("irrelevant", "tempos", False),
    ],
)
def test_transitiontrackfilter_skips_irrelevant_playlists(
    parent_playlist_name,
    playlist_name,
    expected,
):
    """Test for the TransitionTrackFilter class."""
    track_filter = TransitionTrackFilter()
    playlist_class = next(iter(PLATFORM_REGISTRY.values()))["playlist"]
    playlist = playlist_class.new_playlist(playlist_name, tracks={})
    parent_playlist = playlist_class.new_playlist(
        parent_playlist_name, playlists=[playlist]
    )
    playlist.set_parent(parent_playlist)
    result = track_filter.is_filter_playlist(playlist)
    assert result == expected


def test_transitiontrackfilter_handles_playlist_with_multiple_supported_types():
    """Test for the TransitionTrackFilter class."""
    track_filter = TransitionTrackFilter()
    playlist_class = next(iter(PLATFORM_REGISTRY.values()))["playlist"]
    bad_playlist_name = "genres & tempos"
    playlist = playlist_class.new_playlist(bad_playlist_name, tracks={})
    parent_playlist = playlist_class.new_playlist(
        "transitions", playlists=[playlist]
    )
    playlist.set_parent(parent_playlist)
    with pytest.raises(
        ValueError,
        match=(
            f'"{bad_playlist_name}" matches multiple playlist types: genre, '
            "tempo"
        ),
    ):
        track_filter.is_filter_playlist(playlist)


@pytest.mark.parametrize(
    "separator,comments,playlist_type,expected",
    [
        ("/", "[130 / 140]", "tempo", True),
        ("/", "[130 / 140]", "genre", False),
        ("/", "[Techno / Dubstep]", "genre", True),
        ("/", "[Techno / Dubstep]", "tempo", False),
    ],
)
def test_transitiontrackfilter_filters_tracks(
    separator, comments, playlist_type, expected, rekordbox_track
):
    """Test for the TransitionTrackFilter class."""
    track_filter = TransitionTrackFilter(separator)
    playlist_class = next(iter(PLATFORM_REGISTRY.values()))["playlist"]
    rekordbox_track._Comments = comments  # pylint: disable=protected-access
    playlist = playlist_class.new_playlist(
        "genres", tracks={rekordbox_track.get_id(): rekordbox_track}
    )
    root_playlist = playlist_class.new_playlist(
        "transitions", playlists=[playlist]
    )
    playlist.set_parent(root_playlist)
    with mock.patch.object(
        track_filter, "_playlist_type", playlist_type, create=True
    ):
        result = track_filter.filter_track(rekordbox_track)
    assert result == expected
