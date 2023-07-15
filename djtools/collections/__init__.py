"""The `collections` package contains modules:
    * `collections`: abstractions and implementations for collections
    * `config`: the configuration object for the `collections` package
    * `copy_playlists`: copies audio files for tracks within a set of
        playlists to a new location and writes a new collection with these
        updated paths
    * `helpers`: contains helper classes and functions for the other modules of
        this package
    * `playlist_builder`: constructs playlists using tags in a Collection and a
        defined playlist structure in
        `collection_playlists.yaml`
    * `playlists`: abstractions and implementations for playlists
    * `shuffle_playlists`: writes sequential numbers to tags of shuffled tracks
        in playlists to emulate playlist shuffling
    * `tracks`: abstractions and implementations for tracks
"""

from djtools.collections.config import CollectionConfig
from djtools.collections.copy_playlists import copy_playlists
from djtools.collections.playlist_builder import collection_playlists
from djtools.collections.shuffle_playlists import shuffle_playlists


COLLECTION_OPERATIONS = {
    "COLLECTION_PLAYLISTS": collection_playlists,
    "COPY_PLAYLISTS": copy_playlists,
    "SHUFFLE_PLAYLISTS": shuffle_playlists,
}


__all__ = (
    "collection_playlists",
    "CollectionConfig",
    "copy_playlists",
    "shuffle_playlists",
    "COLLECTION_OPERATIONS",
)
