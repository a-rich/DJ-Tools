"""Testing for the tracks module."""
import pytest

from djtools.collections.tracks import Track, RekordboxTrack


def test_track_raises_type_error():
    """Test Track class."""
    with pytest.raises(
        TypeError,
        match=(
            "Can't instantiate abstract class Track with abstract method"
        ),
    ):
        Track()


def test_rekordboxtrack(test_track):
    """Test RekordboxTrack class."""
    test_track["Genre"] = "something / or"
    test_track["Comments"] = "/* another / thing */"
    track = RekordboxTrack(test_track)
    test_track_number = 42
    test_location = "/some/path"
    test_track["TrackNumber"] = str(test_track_number)
    test_track["Location"] = f"file://localhost{test_location}"
    track.set_track_number(test_track_number)
    track.set_location(test_location)
    assert track.get_id() == test_track["TrackID"]
    assert sorted(list(track.get_tags())) == [
        "another", "or", "something", "thing"
    ]
    assert str(test_track) == str(track)
    assert test_track == track.serialize()
    repr(track)
    try:
        RekordboxTrack.validate(test_track, track)
    except AssertionError:
        assert False, "Failed RekordboxTrack validation!"
