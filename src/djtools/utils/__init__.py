"""The "utils" package contains modules for a variety of tasks.
    * check_track_overlap.py: Compares Spotify and / or local files with the
        Beatcloud to identify overlap.
    * config.py: Loading and validate configuration; override with command-line
        arguments.
    * copy_playlists_tracks.py: copies audio files for tracks within a set of
        playlists to a new location and writes a new XML with these updated
        paths.
    * youtube_dl.py: Download tracks from a URL (e.g. Soundcloud playlist).
"""
from djtools.utils.check_track_overlap import compare_tracks
from djtools.utils.config import build_config
from djtools.utils.copy_playlists_tracks import copy_playlists_tracks
from djtools.utils.helpers import upload_log
from djtools.utils.youtube_dl import youtube_dl


UTILS_OPERATIONS = {
    "CHECK_TRACK_OVERLAP": compare_tracks,
    "COPY_PLAYLISTS_TRACKS": copy_playlists_tracks,
    "YOUTUBE_DL_URL": youtube_dl,
}

__all__ = (
    "build_config",
    "compare_tracks",
    "copy_playlists_tracks",
    "UTILS_OPERATIONS",
    "upload_log",
    "youtube_dl",
)
