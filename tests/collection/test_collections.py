"""Testing for the collection module."""
from pathlib import Path

import bs4
import pytest

from djtools.collection.collections import (
    Collection, CustomSubstitution, RekordboxCollection, UnsortedAttributes
)
from djtools.collection.tracks import RekordboxTrack


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
def test_rekordboxcollection(
    rekordbox_xml, rekordbox_collection_tag, playlist
):
    """Test RekordboxCollection class."""
    collection = RekordboxCollection(path=rekordbox_xml)
    tracks = {
        track["TrackID"]: RekordboxTrack(track)
        for track in rekordbox_collection_tag.find_all("TRACK")
        if track.get("Location")
    }
    assert (
        a[0] == b[0] and str(a[1]) == str(b[1])
        for a, b in zip(
            tracks.items(), collection.get_tracks().items()
        )
    )
    repr(collection)
    str(collection)
    playlist = collection.get_playlists(playlist)
    new_path = rekordbox_xml.parent / "test_collection"
    serialized_collection = collection.serialize(output_path=new_path)
    assert new_path.exists()
    RekordboxCollection.validate(rekordbox_xml, serialized_collection)


def test_rekordboxcollection_add_playlist(rekordbox_xml):
    """Test RekordboxCollection class."""
    collection = RekordboxCollection(path=rekordbox_xml)
    num_playlists = len(collection.get_playlists())
    collection.add_playlist([])
    assert len(collection.get_playlists()) == num_playlists + 1


def test_rekordboxcollection_get_all_tags(rekordbox_collection):
    """Test RekordboxCollection class."""
    tracks = rekordbox_collection.get_tracks().values()
    genre_tags, all_tags = set(), set()
    for track in tracks:
        genre_tags.update(track.get_genre_tags())
        all_tags.update(track.get_tags())
    other_tags = all_tags.difference(genre_tags)
    expected = {
        "genres": sorted(genre_tags),
        "other": sorted(other_tags),
    }
    tags = rekordbox_collection.get_all_tags()
    assert tags == expected


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
