"""The `utils` package contains modules:
    * `check_tracks`: Compares Spotify and / or local files with the Beatcloud
        to identify overlap.
    * `config`: the configuration object for the `utils` package
    * `helpers`: helper functions for the `utils` package and the `djtools`
        library in general
    * `youtube_dl`: download tracks from a URL (e.g. Soundcloud playlist).
"""
from djtools.utils.config import UtilsConfig
from djtools.utils.check_tracks import compare_tracks
from djtools.utils.helpers import initialize_logger
from djtools.utils.youtube_dl import youtube_dl


UTILS_OPERATIONS = {
    "CHECK_TRACKS": compare_tracks,
    "YOUTUBE_DL_URL": youtube_dl,
}

__all__ = (
    "compare_tracks",
    "initialize_logger",
    "UtilsConfig",
    "UTILS_OPERATIONS",
    "youtube_dl",
)
