"""The `sync` package contains modules:
    * `config`: the configuration object for the `sync` package
    * `helpers`: helper functions for the `sync_operations` module
    * `sync_operations`: for syncing audio and Rekordbox XML files to the
        Beatcloud
"""
from djtools.sync.config import SyncConfig
from djtools.sync.helpers import upload_log
from djtools.sync.sync_operations import (
    download_music, download_xml, upload_music, upload_xml
)


SYNC_OPERATIONS = {
    'DOWNLOAD_MUSIC': download_music,
    'DOWNLOAD_XML': download_xml,
    'UPLOAD_MUSIC': upload_music,
    'UPLOAD_XML': upload_xml,
}

__all__ = (
    "download_music",
    "download_xml",
    "SyncConfig",
    "SYNC_OPERATIONS",
    "upload_log",
    "upload_music",
    "upload_xml",
)
