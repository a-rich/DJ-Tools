"""Testing for the tracks module."""

import os
from datetime import datetime
from pathlib import Path

import pytest

from djtools.collection.rekordbox_track import RekordboxTrack


@pytest.mark.parametrize(
    "method,expected",
    [
        ("get_artists", "A Tribe Called Quest"),
        ("get_bpm", 86),
        ("get_comments", " /* Gangsta */ "),
        ("get_date_added", datetime(2022, 6, 24)),
        ("get_genre_tags", ["Hip Hop", "R&B"]),
        ("get_id", "2"),
        ("get_key", "7B"),
        ("get_label", "Label"),
        ("get_location", "track2.mp3"),
        ("get_rating", 0),
        ("get_tags", ["Hip Hop", "R&B", "Gangsta"]),
        ("get_year", "2022"),
    ],
)
def test_rekordboxtrack_get_methods(method, expected, rekordbox_track):
    """Test RekordboxTrack class."""
    try:
        _method = getattr(rekordbox_track, method)
    except AttributeError:
        assert False, f"RekordboxTrack is missing required method '{method}'"

    if method == "get_location":
        assert _method().name == expected
    else:
        assert _method() == expected


def test_rekordboxtrack_serialization(rekordbox_track_tag):
    """Test RekordboxTrack class."""
    track = RekordboxTrack(rekordbox_track_tag)
    loc = str(track.get_location())
    assert (
        repr(track)
        == """RekordboxTrack(\n    Artist="A Tribe Called Quest", """
        """AverageBpm=86.0, Comments=" /* Gangsta */ ", """
        """\n    DateAdded="2022-06-24", Genre=['Hip Hop', 'R&B'], """
        f"""Label="Label", Location={loc}, \n    Tonality="7B", Rating=0, """
        """TrackID="2", TrackNumber=2, Year="2022", MyTags=['Gangsta'], """
        """\n    Tags=['Hip Hop', 'R&B', 'Gangsta'], beat_grid=0, hot_cues=0\n)"""
    )
    sep = "" if os.name == "posix" else "/"  # pylint: disable=no-member
    loc = track.get_location().as_posix()
    assert (
        str(track)
        == """<TRACK Artist="A Tribe Called Quest" AverageBpm="86.00" """
        """Comments=" /* Gangsta */ " DateAdded="2022-06-24" """
        """Genre="Hip Hop / R&amp;B" Label="Label" """
        f"""Location="file://localhost{sep}{loc}" Rating="0" Tonality="7B" """
        """TrackID="2" TrackNumber="2" Year="2022"/>"""
    )
    assert track.serialize() == rekordbox_track_tag


def test_rekordboxtrack_set_location(rekordbox_track_tag):
    """Test RekordboxTrack class."""
    track = RekordboxTrack(rekordbox_track_tag)
    track.set_location("path/to.mp3")
    assert track.get_location() == Path("path/to.mp3")


def test_rekordboxtrack_set_track_number(rekordbox_track_tag):
    """Test RekordboxTrack class."""
    track = RekordboxTrack(rekordbox_track_tag)
    track_number = 42
    track.set_track_number(track_number)
    assert f'TrackNumber="{track_number}"' in str(track)
