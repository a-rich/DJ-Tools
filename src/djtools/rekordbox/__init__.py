"""The "rekordbox" package contains modules for operating on exported Rekordbox
databases i.e. rekordbox.xml files.

Included in this package:
    * playlist_builder.py: Automatically create a desired playlist structure
        based on the tags present in an XML.
    * randomize_tracks.py: Set tags of tracks in playlists sequentially
        (after shuffling) to randomize.
"""

from djtools.rekordbox.playlist_builder import rekordbox_playlists
from djtools.rekordbox.randomize_tracks import randomize_tracks


REKORDBOX_OPERATIONS = {
    "RANDOMIZE_TRACKS_PLAYLISTS": randomize_tracks,
    "REKORDBOX_PLAYLISTS": rekordbox_playlists
}

__all__ = "randomize_tracks", "REKORDBOX_OPERATIONS", "rekordbox_playlists"
