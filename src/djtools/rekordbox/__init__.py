"""The "rekordbox" package contains modules for operating on exported Rekordbox
databases i.e. rekordbox.xml files.

Included in this package:
    * randomize_tracks.py: Set tags of tracks in playlists sequentially
        (after shuffling) to randomize.
    * rekordbox_playlist_builder.py: Automatically create a desired playlist
        structure based on the tags present in an XML.
"""

from .randomize_tracks import randomize_tracks
from .rekordbox_playlist_builder import rekordbox_playlists


REKORDBOX_OPERATIONS = {
    "RANDOMIZE_TRACKS": randomize_tracks,
    "REKORDBOX_PLAYLISTS": rekordbox_playlists
}

__all__ = "randomize_tracks", "REKORDBOX_OPERATIONS", "rekordbox_playlists"
