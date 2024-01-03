"""Testing for the playlists module."""
import pytest

from djtools.collection.base_playlist import Playlist


def test_playlist_raises_type_error():
    """Test Playlist class."""
    with pytest.raises(
        TypeError,
        match="Can't instantiate abstract class Playlist",
    ):
        Playlist()
