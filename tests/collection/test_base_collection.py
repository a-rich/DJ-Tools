"""Testing for the collection module."""

import pytest

from djtools.collection.base_collection import Collection


def test_collection_raises_type_error():
    """Test Collection class."""
    with pytest.raises(
        TypeError,
        match="Can't instantiate abstract class Collection",
    ):
        Collection(path="")
