"""Testing for the collection module."""

import bs4

from djtools.collection.rekordbox_collection import (
    CustomSubstitution,
    RekordboxCollection,
    UnsortedAttributes,
)
from djtools.collection.rekordbox_playlist import RekordboxPlaylist
from djtools.collection.rekordbox_track import RekordboxTrack


def test_rekordboxcollection_add_playlist(rekordbox_xml):
    """Test RekordboxCollection class."""
    collection = RekordboxCollection(path=rekordbox_xml)
    num_playlists = len(collection.get_playlists())

    # The test playlist doesn't exist yet.
    test_playlist_name = "TEST"
    assert collection.get_playlists(test_playlist_name) == []

    # The test playlist does exist after inserting it.
    test_playlist = RekordboxPlaylist.new_playlist(
        test_playlist_name, tracks={}
    )
    collection.add_playlist(test_playlist)
    assert collection.get_playlists(test_playlist_name) == [test_playlist]

    # The total playlist count has increased by one.
    assert len(collection.get_playlists()) == num_playlists + 1


def test_rekordboxcollection_get_all_tags(rekordbox_collection):
    """Test RekordboxCollection class."""
    # Manually build the sets of genre tags and other tags from the tracks in
    # the collection.
    tracks = rekordbox_collection.get_tracks().values()
    genre_tags, all_tags = set(), set()
    for track in tracks:
        genre_tags.update(track.get_genre_tags())
        all_tags.update(set(track.get_tags()))
    other_tags = all_tags.difference(genre_tags)

    # Compare the manually constructed tag sets with tag sets returned from the
    # get_all_tags methods.
    expected = {
        "genres": sorted(genre_tags),
        "other": sorted(other_tags),
    }
    tags = rekordbox_collection.get_all_tags()
    assert tags == expected


def test_rekordboxcollection_get_playlists(rekordbox_xml):
    """Test RekordboxCollection class."""
    collection = RekordboxCollection(path=rekordbox_xml)

    # Without being provided any playlists to get, the get_playlists method
    # returns the ROOT playlist.
    assert collection.get_playlists().get_name() == "ROOT"

    # When provided a playlist name, a list containing all the playlists with
    # matching names is returned.
    dark_playlists = collection.get_playlists("Dark")
    for playlist in dark_playlists:
        assert playlist.get_name() == "Dark"


def test_rekordboxcollection_get_tracks(
    rekordbox_xml, rekordbox_collection_tag
):
    """Test RekordboxCollection class."""
    collection = RekordboxCollection(path=rekordbox_xml)

    # Manually construct the track dictionary stored when deserializing a
    # collection.
    tracks = {
        track["TrackID"]: RekordboxTrack(track)
        for track in rekordbox_collection_tag.find_all("TRACK")
        if track.get("Location")
    }

    # Compare the manually constructed track dictionary with the one internal
    # to the deserialized collection.
    assert (
        a[0] == b[0] and str(a[1]) == str(b[1])
        for a, b in zip(tracks.items(), collection.get_tracks().items())
    )


def test_rekordboxcollection_serialization(rekordbox_xml):
    """Test RekordboxCollection class."""
    collection = RekordboxCollection(path=rekordbox_xml)

    assert (
        repr(collection)
        == f"""RekordboxCollection(
    path="{rekordbox_xml}",
    tracks=4,
    playlists=3,
)"""
    )

    # Serializing a collection returns the path to the serialized collection
    # which will overwrite the path from which the collection was deserialized
    # from...
    assert collection.serialize() == rekordbox_xml

    # ...unless a different path is provided explicitly.
    new_path = rekordbox_xml.parent / "test_collection"
    serialized_collection = collection.serialize(path=new_path)
    assert new_path.exists()
    assert rekordbox_xml != serialized_collection

    # Serialization / deserialization is a symmetrical operation.
    try:
        RekordboxCollection.validate(rekordbox_xml, serialized_collection)
    except AssertionError:
        assert False, "RekordboxCollection validation failed!"


def test_rekordboxcollection_set_tracks(rekordbox_xml):
    """Test RekordboxCollection class."""
    collection = RekordboxCollection(path=rekordbox_xml)

    # Get the original set of tracks.
    original_tracks = collection.get_tracks()

    # Create a new dictionary of tracks which contains only one (key, value)
    # pair.
    new_tracks = {}
    for key, value in original_tracks.items():
        new_tracks[key] = value
        break

    # Set the collections tracks to this new subset of tracks.
    collection.set_tracks(new_tracks)

    # The new tracks are different from the original tracks.
    assert new_tracks != original_tracks

    # The collection now returns the new tracks.
    assert collection.get_tracks() == new_tracks


def test_customsubstitution():
    """Test CustomSubstitution class."""
    test_string = """Bob's cat is "cute" & <furry>"""
    expected = "Bob&apos;s cat is &quot;cute&quot; &amp; &lt;furry&gt;"
    result = CustomSubstitution.substitute_xml(test_string)
    assert result == expected


def test_unsortedattributes_formatter():
    """Test UnsortedAttributes class."""
    expected = '<NODE Z_attr="" A_attr="">\n</NODE>\n'
    a_first_tag = bs4.Tag(name="NODE", attrs={"A_attr": "", "Z_attr": ""})
    z_first_tag = bs4.Tag(name="NODE", attrs={"Z_attr": "", "A_attr": ""})
    # BeautifulSoup alphabetizes attributes by default.
    assert str(z_first_tag) == str(a_first_tag)
    # Using UnsortedAttributes formatter will cause the Tag to render the
    # attributes in their original order.
    assert z_first_tag.prettify(formatter=UnsortedAttributes()) == expected
