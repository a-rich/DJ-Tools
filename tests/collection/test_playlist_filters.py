"""Testing for the playlist_filters module."""
from unittest import mock

import pytest

from djtools.collection.playlist_filters import (
    HipHopFilter,
    MinimalDeepTechFilter,
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
