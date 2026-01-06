"""This module contains the platform registry for supported DJ software."""

from djtools.collection.config import RegisteredPlatforms
from djtools.collection.rekordbox_collection import RekordboxCollection
from djtools.collection.rekordbox_playlist import RekordboxPlaylist
from djtools.collection.rekordbox_track import RekordboxTrack

# As support for various platforms (Serato, Denon, Traktor, etc.) is added, the
# platform name must be registered with references to their Collection,
# Playlist, and Track implementations.
PLATFORM_REGISTRY = {
    RegisteredPlatforms.REKORDBOX: {
        "collection": RekordboxCollection,
        "playlist": RekordboxPlaylist,
        "track": RekordboxTrack,
    },
}
