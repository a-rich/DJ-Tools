"""Testing for the playlist_filters module."""

from unittest import mock

import pytest

from djtools.collection.playlist_filters import (
    ComplexTrackFilter,
    HipHopFilter,
    MinimalDeepTechFilter,
    PlaylistFilter,
    TransitionTrackFilter,
)
from djtools.collection.rekordbox_playlist import RekordboxPlaylist
from djtools.collection.rekordbox_track import RekordboxTrack


def test_playlistfilter_cannot_be_instantiated():
    """Test for the PlaylistFilter class."""
    with pytest.raises(
        TypeError,
        match="Can't instantiate abstract class PlaylistFilter",
    ):
        PlaylistFilter()


@pytest.mark.parametrize(
    "parent_playlist,playlist,hip_hop_playlist,bass_hip_hop_playlist",
    [
        ("Bass", "Hip Hop", True, True),
        ("Not Bass", "Hip Hop", True, False),
        ("something", "irrelevant", False, False),
    ],
)
def test_hiphopfilter_detects_playlists(
    parent_playlist,
    playlist,
    hip_hop_playlist,
    bass_hip_hop_playlist,
):
    """Test for the HipHopFilter class."""
    track_filter = HipHopFilter()
    playlist = RekordboxPlaylist.new_playlist(playlist, tracks={})
    parent_playlist = RekordboxPlaylist.new_playlist(
        parent_playlist, playlists=[playlist]
    )
    playlist.set_parent(parent_playlist)
    result = track_filter.is_filter_playlist(playlist)
    assert result == hip_hop_playlist
    assert (
        track_filter._bass_hip_hop  # pylint: disable=protected-access
        == bass_hip_hop_playlist
    )


@pytest.mark.parametrize(
    "bass_hip_hop,tags,expected",
    [
        (True, ["Hip Hop", "R&B"], False),
        (True, ["Hip Hop", "Trap"], True),
        (False, ["Hip Hop", "R&B"], True),
        (False, ["Hip Hop", "Trap"], False),
    ],
)
def test_hiphopfilter_filters_tracks(
    bass_hip_hop, tags, expected, rekordbox_track
):
    """Test for the HipHopFilter class."""
    track_filter = HipHopFilter()
    with (
        mock.patch.object(
            track_filter, "_bass_hip_hop", bass_hip_hop, create=True
        ),
        mock.patch.object(RekordboxTrack, "get_genre_tags", lambda x: tags),
    ):
        result = track_filter.filter_track(rekordbox_track)
        assert result == expected


@pytest.mark.parametrize(
    "parent_playlist,playlist,minimal_deep_tech_playlist",
    [
        ("Techno", "Minimal Deep Tech", True),
        ("House", "Minimal Deep Tech", True),
        ("Techno", "Something", False),
        ("House", "Something", False),
        ("Something", "Minimal Deep Tech", False),
    ],
)
def test_minimaldeeptechfilter_detects_playlists(
    parent_playlist,
    playlist,
    minimal_deep_tech_playlist,
):
    """Test for the MinimalDeepTechFilter class."""
    track_filter = MinimalDeepTechFilter()
    playlist = RekordboxPlaylist.new_playlist(playlist, tracks={})
    parent_playlist = RekordboxPlaylist.new_playlist(
        parent_playlist, playlists=[playlist]
    )
    playlist.set_parent(parent_playlist)
    result = track_filter.is_filter_playlist(playlist)
    techno_playlist = (
        parent_playlist.get_name() == "Techno" and minimal_deep_tech_playlist
    )
    house_playlist = (
        parent_playlist.get_name() == "House" and minimal_deep_tech_playlist
    )
    assert result == minimal_deep_tech_playlist
    assert (
        track_filter._techno  # pylint: disable=protected-access
        == techno_playlist
    )
    assert (
        track_filter._house  # pylint: disable=protected-access
        == house_playlist
    )


@pytest.mark.parametrize(
    "techno,tags,expected",
    [
        (True, ["Techno", "Minimal Deep Tech"], True),
        (True, ["House", "Minimal Deep Tech"], False),
        (False, ["Techno", "Minimal Deep Tech"], False),
        (False, ["House", "Minimal Deep Tech"], True),
    ],
)
def test_minimaldeeptechfilter_filters_tracks(
    techno, tags, expected, rekordbox_track
):
    """Test for the MinimalDeepTechFilter class."""
    track_filter = MinimalDeepTechFilter()
    with (
        mock.patch.object(track_filter, "_techno", techno, create=True),
        mock.patch.object(track_filter, "_house", not techno, create=True),
        mock.patch.object(RekordboxTrack, "get_genre_tags", lambda x: tags),
    ):
        result = track_filter.filter_track(rekordbox_track)
        assert result == expected


@pytest.mark.parametrize(
    "parent_playlist,playlist,expected",
    [
        ("something", "complex", True),
        ("complex", "irrelevant", True),
        ("irrelevant", "something", False),
    ],
)
def test_complextrackfilter_detects_playlists(
    parent_playlist,
    playlist,
    expected,
):
    """Test for the ComplexTrackFilter class."""
    track_filter = ComplexTrackFilter()
    playlist = RekordboxPlaylist.new_playlist(playlist, tracks={})
    parent_playlist = RekordboxPlaylist.new_playlist(
        parent_playlist, playlists=[playlist]
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
    rekordbox_track._Tags = tags  # pylint: disable=protected-access
    playlist = RekordboxPlaylist.new_playlist(
        "genres", tracks={rekordbox_track.get_id(): rekordbox_track}
    )
    root_playlist = RekordboxPlaylist.new_playlist(
        "complex", playlists=[playlist]
    )
    playlist.set_parent(root_playlist)
    result = track_filter.filter_track(rekordbox_track)
    assert result == expected


@pytest.mark.parametrize(
    "parent_playlist,playlist,expected",
    [
        ("transitions", "genres", True),
        ("transitions", "tempos", True),
        ("irrelevant", "transitions", False),
        ("irrelevant", "genres", False),
        ("irrelevant", "tempos", False),
    ],
)
def test_transitiontrackfilter_detects_playlists(
    parent_playlist,
    playlist,
    expected,
):
    """Test for the TransitionTrackFilter class."""
    track_filter = TransitionTrackFilter()
    playlist = RekordboxPlaylist.new_playlist(playlist, tracks={})
    parent_playlist = RekordboxPlaylist.new_playlist(
        parent_playlist, playlists=[playlist]
    )
    playlist.set_parent(parent_playlist)
    result = track_filter.is_filter_playlist(playlist)
    assert result == expected


def test_transitiontrackfilter_handles_playlist_with_multiple_supported_types():
    """Test for the TransitionTrackFilter class."""
    track_filter = TransitionTrackFilter()
    bad_playlist = "genres & tempos"
    playlist = RekordboxPlaylist.new_playlist(bad_playlist, tracks={})
    parent_playlist = RekordboxPlaylist.new_playlist(
        "transitions", playlists=[playlist]
    )
    playlist.set_parent(parent_playlist)
    with pytest.raises(
        ValueError,
        match=(
            f'"{bad_playlist}" matches multiple playlist types: genre, '
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
    rekordbox_track._Comments = comments  # pylint: disable=protected-access
    playlist = RekordboxPlaylist.new_playlist(
        "genres", tracks={rekordbox_track.get_id(): rekordbox_track}
    )
    root_playlist = RekordboxPlaylist.new_playlist(
        "transitions", playlists=[playlist]
    )
    playlist.set_parent(root_playlist)
    with mock.patch.object(
        track_filter, "_playlist_type", playlist_type, create=True
    ):
        result = track_filter.filter_track(rekordbox_track)
    assert result == expected
