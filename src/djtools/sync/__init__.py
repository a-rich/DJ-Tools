"""The `sync` package contains modules:
    * `config`: the configuration object for the `sync` package
    * `helpers`: helper functions for the `sync_operations` module
    * `sync_operations`: for syncing audio and collection files to the
        Beatcloud
"""

from djtools.sync.sync_operations import (
    download_collection,
    download_music,
    upload_collection,
    upload_music,
)


SYNC_OPERATIONS = {
    "download_collection": download_collection,
    "download_music": download_music,
    "download_spotify_playlist": download_music,
    "upload_collection": upload_collection,
    "upload_music": upload_music,
}

__all__ = (
    "download_collection",
    "download_music",
    "upload_collection",
    "upload_music",
)
