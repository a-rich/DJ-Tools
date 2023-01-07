"""The `rekordbox` package contains modules:
    * `config`: the configuration object for the `rekordbox` package
    * `copy_tracks_playlists`: copies audio files for tracks within a set of
        playlists to a new location and writes a new XML with these updated
        paths
    * `helpers`: contains helper classes and functions for the other modules of
        this package
    * `playlist_builder`: constructs rekordbox playlists using tags in a
        Collection and a defined playlist structure in
        `rekordbox_playlists.yaml`
    * `randomize_tracks`: writes sequential numbers to Rekordbox tags of
        shuffled tracks in playlists to emulate playlist shuffling
    * `tag_parsers`: the `TagParser` abstract base class and its
        implementations used by the `playlist_builder`
"""

from djtools.rekordbox.config import RekordboxConfig
from djtools.rekordbox.copy_tracks_playlists import copy_tracks_playlists
from djtools.rekordbox.playlist_builder import rekordbox_playlists
from djtools.rekordbox.randomize_tracks import randomize_tracks


REKORDBOX_OPERATIONS = {
    "COPY_TRACKS_PLAYLISTS": copy_tracks_playlists,
    "RANDOMIZE_TRACKS_PLAYLISTS": randomize_tracks,
    "REKORDBOX_PLAYLISTS": rekordbox_playlists
}

__all__ = (
    "copy_tracks_playlists",
    "randomize_tracks",
    "RekordboxConfig",
    "REKORDBOX_OPERATIONS",
    "rekordbox_playlists",
)
