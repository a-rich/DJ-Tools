"""The `utils` package contains modules:
    * `check_tracks`: Compares Spotify and / or local files with the Beatcloud
        to identify overlap.
    * `config`: the configuration object for the `utils` package
    * `helpers`: helper functions for the `utils` package and the `djtools`
        library in general
    * `url_download`: download tracks from a URL (e.g. Soundcloud playlist).
"""
from djtools.utils.config import UtilsConfig
from djtools.utils.check_tracks import compare_tracks
from djtools.utils.helpers import initialize_logger
from djtools.utils.url_download import url_download


UTILS_OPERATIONS = {
    "CHECK_TRACKS": compare_tracks,
    "URL_DOWNLOAD": url_download,
}

__all__ = (
    "compare_tracks",
    "initialize_logger",
    "url_download",
    "UtilsConfig",
    "UTILS_OPERATIONS",
)
