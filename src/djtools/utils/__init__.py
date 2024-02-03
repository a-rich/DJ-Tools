"""The `utils` package contains modules:
    * `check_tracks`: Compares Spotify and / or local files with the Beatcloud
        to identify overlap.
    * `config`: the configuration object for the `utils` package
    * `helpers`: helper functions for the `utils` package and the `djtools`
        library in general
    * `normalize_audio`: sets the peak amplitude of tracks go a configured
        headroom and exports them with a configured bit rate and file format.
    * `process_recording`: given a Spotify playlist and a recording file, chunk
        the recording into individual tracks, normalize their peak amplitude
        with the configured headroom, and export them with the configured
        bit rate and file format.
    * `url_download`: download tracks from a URL (e.g. Soundcloud playlist).
"""

from djtools.utils.check_tracks import compare_tracks
from djtools.utils.normalize_audio import normalize
from djtools.utils.process_recording import process
from djtools.utils.url_download import url_download


UTILS_OPERATIONS = {
    "CHECK_TRACKS": compare_tracks,
    "NORMALIZE_AUDIO": normalize,
    "PROCESS_RECORDING": process,
    "URL_DOWNLOAD": url_download,
}

__all__ = (
    "compare_tracks",
    "normalize",
    "process",
    "url_download",
)
