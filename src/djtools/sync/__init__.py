"""The 'sync' package contains a module for syncing tracks to and from the
beatcloud, syncing USER's XML to the beatcloud, and syncing XML_IMPORT_USER's
XML to the parent directory of 'XML_PATH'. It also contains a module of helper
functions used by the former module.
"""
from .sync_operations import (
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
    "SYNC_OPERATIONS",
    "upload_music",
    "upload_xml",
)
