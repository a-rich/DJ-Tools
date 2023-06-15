"""Testing for the collections module."""
from pathlib import Path

import bs4
import pytest

from djtools.collections.collections import (
    Collection, CustomSubstitution, RekordboxCollection, UnsortedAttributes
)
from djtools.collections.tracks import RekordboxTrack


def test_collection_raises_type_error():
    """Test Collection class."""
    with pytest.raises(
        TypeError,
        match=(
            "Can't instantiate abstract class Collection with abstract method"
        ),
    ):
        Collection(path=Path())


def test_customsubstitution():
    """Test CustomSubstitution class."""
    test_string = '''Bob's cat is "cute" & <furry>'''
    expected = "Bob&apos;s cat is &quot;cute&quot; &amp; &lt;furry&gt;"
    result = CustomSubstitution.substitute_xml(test_string)
    assert result == expected


@pytest.mark.parametrize("playlist", ["Genres", "Hip Hop"])
def test_rekordboxcollection(test_xml, xml, playlist):
    """Test RekordboxCollection class."""
    collection = RekordboxCollection(path=test_xml)
    test_tracks = {
        track["TrackID"]: RekordboxTrack(track)
        for track in xml.find_all("TRACK") if track.get("Location")
    }
    assert (
        a[0] == b[0] and str(a[1]) == str(b[1])
        for a, b in zip(
            test_tracks.items(), collection.get_tracks().items()
        )
    )
    repr(collection)
    str(collection)
    playlist = collection.get_playlists(playlist)
    serialized_collection = collection.serialize()
    assert serialized_collection.exists()
    try:
        RekordboxCollection.validate(test_xml, serialized_collection)
    except AssertionError:
        assert False, "Failed RekordboxCollection validation!"


def test_rekordboxcollection_add_playlist(test_xml):
    """Test RekordboxCollection class."""
    collection = RekordboxCollection(path=test_xml)
    collection.reset_playlists()
    assert len(collection.get_playlists()) == 0
    collection.add_playlist([])
    assert len(collection.get_playlists()) == 1


def test_rekordboxcollection_reset_playlists(test_xml, xml):
    """Test RekordboxCollection class."""
    collection = RekordboxCollection(path=test_xml)
    top_level_playlists = [
        child for child in xml.find("NODE", {"Name": "ROOT"}).children
        if isinstance(child, bs4.element.Tag)
    ]
    assert len(collection.get_playlists()) == len(top_level_playlists)
    collection.reset_playlists()
    assert len(collection.get_playlists()) == 0


def test_unsortedattributes_formatter():
    """Test UnsortedAttributes class."""
    expected = '<NODE Z_attr="" A_attr="">\n</NODE>'
    a_first_tag = bs4.Tag(name="NODE", attrs={"A_attr": "", "Z_attr": ""})
    z_first_tag = bs4.Tag(name="NODE", attrs={"Z_attr": "", "A_attr": ""})
    # BeautifulSoup alphabetizes attributes by default.
    assert str(z_first_tag) == str(a_first_tag)
    # Using UnsortedAttributes formatter will cause the Tag to render the
    # attributes in their original order.
    assert z_first_tag.prettify(formatter=UnsortedAttributes()) == expected
