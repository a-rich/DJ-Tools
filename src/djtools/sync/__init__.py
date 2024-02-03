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
    "DOWNLOAD_COLLECTION": download_collection,
    "DOWNLOAD_MUSIC": download_music,
    "DOWNLOAD_SPOTIFY_PLAYLIST": download_music,
    "UPLOAD_COLLECTION": upload_collection,
    "UPLOAD_MUSIC": upload_music,
}

__all__ = (
    "download_collection",
    "download_music",
    "upload_collection",
    "upload_music",
)
