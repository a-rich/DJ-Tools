"""This is the main function which runs the configured operations of `djtools`.

The logger is initialized from a configuration file. Then `config.yaml` is read
(if it exists) and the individual packages' configuration objects are
instantiated. The optional C extension to accelerate edit distance computation,
Levenshtein, is imported. The loop iterates all the supported top-level
operations of the library and calls the corresponding function with the
appropriate configuration object. Finally, the log file generated from this run
is uploaded to the Beatcloud.
"""
from .configs import build_config
from .rekordbox import (
    build_playlists,
    copy_playlists,
    REKORDBOX_OPERATIONS,
    shuffle_playlists,
)
from .spotify import (
    playlist_from_upload,
    SPOTIFY_OPERATIONS,
    update_auto_playlists,
)
from .sync import (
    download_music,
    download_xml,
    SYNC_OPERATIONS,
    upload_log,
    upload_music,
    upload_xml,
)
from .utils import (
    compare_tracks,
    initialize_logger,
    UTILS_OPERATIONS,
    url_download,
)


__all__ = (
    "build_config",
    "build_playlists",
    "compare_tracks",
    "copy_playlists",
    "download_music",
    "download_xml",
    "initialize_logger",
    "playlist_from_upload",
    "REKORDBOX_OPERATIONS",
    "shuffle_playlists",
    "SPOTIFY_OPERATIONS",
    "SYNC_OPERATIONS",
    "update_auto_playlists",
    "upload_log",
    "upload_music",
    "upload_xml",
    "UTILS_OPERATIONS",
    "url_download",
)


def main():
    """This is the entry point for the DJ Tools library."""

    logger, log_file = initialize_logger()
    config = build_config()
    logger.setLevel(config.LOG_LEVEL)

    # Run "rekordbox", "spotify", "sync", and "utils" package operations if any
    # of the flags to do so are present in the config.
    beatcloud_cache = []
    for package in [
        REKORDBOX_OPERATIONS,
        SPOTIFY_OPERATIONS,
        UTILS_OPERATIONS,
        SYNC_OPERATIONS,
    ]:
        for operation, func in package.items():
            if not getattr(config, operation):
                continue
            logger.info(f"{operation}")
            if operation in ["CHECK_TRACKS", "DOWNLOAD_MUSIC"]:
                beatcloud_cache = func(  # pylint: disable=assignment-from-no-return,unexpected-keyword-arg
                    config, beatcloud_tracks=beatcloud_cache
                )
            else:
                func(config)

    upload_log(config, log_file)
