"""This is the main function which runs the configured operations of `djtools`.

The logger is initialized from a configuration file. Then `config.yaml` is read
(if it exists) and the individual packages' configuration objects are
instantiated. The optional C extension to accelerate edit distance computation,
Levenshtein, is imported. The loop iterates all the supported top-level
operations of the library and calls the corresponding function with the
appropriate configuration object. Finally, the log file generated from this run
is uploaded to the Beatcloud.
"""
from djtools import (
    build_config,
    initialize_logger,
    REKORDBOX_OPERATIONS,
    SPOTIFY_OPERATIONS,
    SYNC_OPERATIONS,
    upload_log,
    UTILS_OPERATIONS,
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
                beatcloud_cache = func(
                    config, beatcloud_tracks=beatcloud_cache
                )
            else:
                func(config)

    upload_log(config, log_file)
