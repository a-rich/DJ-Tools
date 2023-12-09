"""Testing for the tracks module."""
import re
import os
from pathlib import Path
from urllib.parse import unquote

import pytest

from djtools.collection.tracks import Track, RekordboxTrack


def test_track_raises_type_error():
    """Test Track class."""
    with pytest.raises(
        TypeError,
        match=("Can't instantiate abstract class Track with abstract method"),
    ):
        Track()


def test_rekordboxtrack(rekordbox_track, rekordbox_track_tag):
    """Test RekordboxTrack class."""
    prefix = "file://localhost" if os.name == "posix" else "file://localhost/"
    track = RekordboxTrack(rekordbox_track_tag)
    RekordboxTrack.validate(rekordbox_track_tag, track)
    RekordboxTrack.validate(track.serialize(), rekordbox_track)
    assert repr(track) == repr(rekordbox_track)
    assert str(track) == str(rekordbox_track)
    assert track.get_bpm() == float(rekordbox_track_tag["AverageBpm"])
    genre_tags = list(map(str.strip, rekordbox_track_tag["Genre"].split("/")))
    assert track.get_genre_tags() == genre_tags
    assert track.get_id() == rekordbox_track_tag["TrackID"]
    assert track.get_location() == Path(
        unquote(rekordbox_track_tag["Location"]).split(prefix)[-1]
    )
    assert track.get_rating() == {
        "0": 0,
        "51": 1,
        "102": 2,
        "153": 3,
        "204": 4,
        "255": 5,
    }.get(rekordbox_track_tag["Rating"])
    tags = re.search(r"(?<=\/\*).*(?=\*\/)", rekordbox_track_tag["Comments"])
    tags = [x.strip() for x in tags.group().split("/")] if tags else []
    assert track.get_tags() == genre_tags + tags
    track.set_location("path/to.mp3")
    assert track.get_location() == Path("path/to.mp3")
    track_number = 42
    track.set_track_number(track_number)
    assert f'TrackNumber="{track_number}"' in str(track)
