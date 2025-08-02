"""Testing for the playlists module."""

import pytest

from djtools.collection.base_playlist import Playlist


# pylint:disable=missing-class-docstring,no-method-argument,arguments-differ,protected-access


def test_playlist_raises_type_error():
    """Test Playlist class."""
    with pytest.raises(
        TypeError,
        match="Can't instantiate abstract class Playlist",
    ):
        Playlist()


@pytest.mark.parametrize("enable_aggregation", [True, False])
def test_playlist_adds_aggregate_attribute(enable_aggregation):
    """Test Playlist class."""

    class ConcretePlaylist(Playlist):
        def get_name():
            pass

        def is_folder():
            pass

        def new_playlist():
            pass

        def serialize():
            pass

    playlist = ConcretePlaylist(enable_aggregation=enable_aggregation)
    assert playlist._aggregate == enable_aggregation
