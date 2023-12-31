# Adding DJ Software Support to the Collections Package


## Contents
- [Overview](#overview)
- [Collections](#collections)
- [Tracks](#tracks)
- [Playlists](#playlists)
- [Appendix: Rekordbox as an example](#rekordbox-as-an-example)
    - [RekordboxCollection](#rekordboxcollection)
    - [RekordboxTrack](#rekordboxtrack)
    - [RekordboxPlaylist](#rekordboxplaylist)


## Overview
The `collection` package is designed to work with any serialized DJ collection that contains all the information about tracks and playlists.
Each of these three components, `Collection`, `Playlist`, and `Track`, has an interface with which `djtools` uses to implement [these features](../how_to_guides/index.md#collection).

In order to extend `djtools` so that these features can be used for other DJ platforms (Denon, Serato, Traktor, Virtual DJ, etc.), these three components must be subclassed to implement several abstract methods. 


## Collections
Every `Collection` subclass must implement an `__init__` that accepts a `pathlib.Path` (or a `str` if you decorate it with `@make_path`).
The `__init__` must deserialize the `Track` and `Playlist` data under the `Path` to create a `Collection` object.

The other method a `Collection` must implement is `serialize` which will write the `Collection` data in whatever format is native for that DJ platform and return the `Path` to it.

::: djtools.collection.base_collection.Collection.serialize
    options:
        show_docstring_description: false
        show_docstring_parameters: false
        show_docstring_returns: false

---

Subclasses of `Collection` inherit a few methods necessary to execute on the `djtools` feature set:

###### Appending a `Playlist` object to the root `Playlist`:
::: djtools.collection.base_collection.Collection.add_playlist
    options:
        show_docstring_description: false
        show_docstring_parameters: false
###### Getting the root `Playlist` or, if a `name` is provided, the list of `Playlist` objects with matching names (supports fuzzy matching with the `glob` parameter):
::: djtools.collection.base_collection.Collection.get_playlists
    options:
        show_docstring_description: false
        show_docstring_parameters: false
        show_docstring_returns: false
###### Getting the dictionary mapping track IDs to `Track` objects:
::: djtools.collection.base_collection.Collection.get_tracks
    options:
        show_docstring_description: false
        show_docstring_returns: false
###### Set the dictionary mapping track IDs to `Track` objects:
::: djtools.collection.base_collection.Collection.set_tracks
    options:
        show_docstring_description: false
        show_docstring_parameters: false
###### Get a dictionary with the sorted set of genre tags and non-genre tags:
::: djtools.collection.base_collection.Collection.get_all_tags
    options:
        show_docstring_description: false
        show_docstring_returns: false


## Tracks
Subclasses of the `Track` class have 16 abstract methods to be implemented, but 14 of those methods are simple getters or setters.
The two primary abstract methods are, again, `__init__` and `serialize`.

The requirements for a `Track` subclass' initialization are only that it parses from the input object the dozen or so attributes that the other abstract methods either get or set:

A `Track` subclass must implement a `serialize` which returns an exact match of the input object used with `__init__`. In other words, it must be the case that `input == Track(input).serialize()`:

::: djtools.collection.base_track.Track.serialize
    options:
        show_docstring_description: false
        show_docstring_returns: false

Let's not enumerate the many getter and setters of the `Track` object here, but you can check them out for yourself:

::: djtools.collection.base_track.Track
    options:
        show_bases: false
        members: false
        show_docstring_description: false


## Playlists 
A subclass of the `Playlist` class must implement five abstract methods for working with a recursive playlist structure.
Like the other components of a collection, the `Playlist` class also requires an `__init__` and `serialize` implementation.

The `__init__` method must take an input that's either a playlist folder or a playlist that contains tracks:

As with `Track`, `Playlist` subclasses must implement a `serialize` which returns an exact match of the input object used with `__init__`. In other words, it must be the case that `input == Playlist(input).serialize()`:

::: djtools.collection.base_playlist.Playlist.serialize
    options:
        show_docstring_description: false
        show_docstring_returns: false

---

The other abstract methods that must be implemented are:

The `get_name` and the `is_folder` methods are a simple getter and condition check:

::: djtools.collection.base_playlist.Playlist.get_name
    options:
        show_docstring_description: false
        show_docstring_returns: false

::: djtools.collection.base_playlist.Playlist.is_folder
    options:
        show_docstring_description: false
        show_docstring_returns: false

A class method called `new_playlist` which can create a `Playlist` object from either a list of `Playlist` objects or a dictionary of `Track` objects:

::: djtools.collection.base_playlist.Playlist.new_playlist
    options:
        show_docstring_description: false
        show_docstring_parameters: false
        show_docstring_raises: false
        show_docstring_returns: false


## Appendix


### Rekordbox as an example


#### RekordboxCollection
Rekordbox supports exporting a collection to an XML file which contains two primary sections: a COLLECTION tag with TRACK tags, and a PLAYLISTS tag with NODE tags with either more NODE tags or TRACK tags that have a key referencing the COLLECTION TRACKS. A [minimal example XML](https://github.com/a-rich/DJ-Tools/blob/main/tests/data/rekordbox.xml) can be seen in the test data.

The `RekordboxCollection` implements `__init__` by parsing the XML with BeautifulSoup, deserializing the tracks as a dictionary of `RekordboxTrack` objects, and deserializing the playlists into the root node of a `RekordboxPlaylist` tree:

The `serialize` method of `RekordboxCollection` builds a new XML document, populates the COLLECTION tag by serializing the values of the `RekordboxTrack` dictionary, and then populates the PLAYLISTS tag by iterating the root `RekordboxPlaylist` and serializing its children:

::: djtools.collection.rekordbox_collection.RekordboxCollection.serialize
    options:
        show_docstring_description: false
        show_docstring_parameters: false
        show_docstring_returns: false


#### RekordboxTrack
A track in an XML contains all the information about tracks except for what playlists they belong to. This information is stored directly in the attributes of the TRACK tag with the exception of the beat grid and hot cue data which are represented as sub-tags TEMPO and POSITION_MARK, respectively.

The `RekordboxTrack` implements `__init__` by enumerating the attributes of the input Track tag and deserializing the string values as types that are more useful in Python, such as `datetime` objects, `lists`, `sets`, and numerical values:

The `serialize` method of `RekordboxTrack` builds a new XML tag for a TRACK and populates the attributes of that tag using the `RekordboxTrack` members. Because Rekordbox serializes TRACK tags inside of the PLAYLISTS differently, this method accepts a parameter to indicate that the `RekordboxTrack` should serialize containing only its ID:

::: djtools.collection.rekordbox_track.RekordboxTrack.serialize
    options:
        show_docstring_description: false
        show_docstring_parameters: false
        show_docstring_raises: false
        show_docstring_returns: false


#### RekordboxPlaylist
A playlist in an XML is a NODE tag which is a recursive structure that contains other NODE tags. The leaves of this tree are NODE tags which contain only TRACK tags with just a single attribute, KEY, which maps to the TrackID attribute of the TRACK tags under the COLLECTION tag.

NODE tags also have attributes for the Name and Type (folder or not) and either a Count or an Entries attribute which has the number of playlists or number of tracks, respectively.

The `__init__` method deserializes a NODE tag by either recursively deserializing its children NODE tags (if it's a folder) or else creating a dictionary of tracks from `RekordboxCollection` object's tracks passed as a parameter:

The `new_playlist` method creates a new Node tag and deserializes it as a `RekordboxPlaylist` before setting its members with either a `RekordboxTrack` dictionary or a list of `RekordboxPlaylist` objects:

::: djtools.collection.rekordbox_playlist.RekordboxPlaylist.new_playlist
    options:
        show_docstring_description: false
        show_docstring_parameters: false
        show_docstring_raises: false
        show_docstring_returns: false
    
The `serialize` method of `RekordboxPlaylist` builds a new XML tag for a NODE and populates the attributes and sub-tags recursively:

::: djtools.collection.rekordbox_playlist.RekordboxPlaylist.serialize
    options:
        show_docstring_description: false
        show_docstring_returns: false
