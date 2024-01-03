"""The `collection` package contains modules:

    * `base_collection`: abstraction for Collection
    * `base_playlist`: abstraction for Playlist
    * `base_track`: abstraction for Track
    * `config`: the configuration object for the `collection` package
    * `copy_playlists`: copies audio files for tracks within a set of
        playlists to a new location and writes a new collection with these
        updated paths
    * `helpers`: contains helper classes and functions for the other modules of
        this package
    * `playlist_builder`: constructs playlists using tags in a Collection and a
        defined playlist structure in
        `collection_playlists.yaml`
    * `playlist_filters`: abstractions and implementations for playlist filters
    * `playlists`: abstractions and implementations for playlists
    * `rekordbox_collection`: implementation of Collection for Rekordbox
    * `rekordbox_playlist`: implementation of Playlist for Rekordbox
    * `rekordbox_track`: implementation of Track for Rekordbox
    * `shuffle_playlists`: writes sequential numbers to tags of shuffled tracks
        in playlists to emulate playlist shuffling
    * `tracks`: abstractions and implementations for tracks
"""

from djtools.collection.copy_playlists import copy_playlists
from djtools.collection.playlist_builder import collection_playlists
from djtools.collection.rekordbox_collection import RekordboxCollection
from djtools.collection.rekordbox_playlist import RekordboxPlaylist
from djtools.collection.rekordbox_track import RekordboxTrack
from djtools.collection.shuffle_playlists import shuffle_playlists


COLLECTION_OPERATIONS = {
    "COLLECTION_PLAYLISTS": collection_playlists,
    "COPY_PLAYLISTS": copy_playlists,
    "SHUFFLE_PLAYLISTS": shuffle_playlists,
}


__all__ = (
    "collection_playlists",
    "copy_playlists",
    "RekordboxCollection",
    "RekordboxPlaylist",
    "RekordboxTrack",
    "shuffle_playlists",
)
