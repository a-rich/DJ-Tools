"""Testing for the tracks module."""

import pytest

from djtools.collection.base_track import Track


def test_track_raises_type_error():
    """Test Track class."""
    with pytest.raises(
        TypeError,
        match="Can't instantiate abstract class Track",
    ):
        Track()
