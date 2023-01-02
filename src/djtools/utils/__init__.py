"""The "utils" package contains modules for a variety of different tasks.
    * local_dirs_checker.py: Check local tracks for overlap with those already
        in the beatcloud.
    * youtube_dl.py: Download tracks from a URL (e.g. Soundcloud playlist).
"""
from .config import build_config
from .helpers import compare_tracks, upload_log
from .copy_playlists_tracks import copy_playlists_tracks
from .youtube_dl import youtube_dl


UTILS_OPERATIONS = {
    "CHECK_TRACK_OVERLAP": compare_tracks,
    "COPY_PLAYLISTS_TRACKS": copy_playlists_tracks,
    "YOUTUBE_DL": youtube_dl,
}

__all__ = (
    "build_config",
    "compare_tracks",
    "copy_playlists_tracks",
    "UTILS_OPERATIONS",
    "upload_log",
    "youtube_dl",
)
