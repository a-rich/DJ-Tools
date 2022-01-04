"""The 'sync' package contains a module for syncing tracks to and from the
beatcloud, syncing USER's XML to the beatcloud, and syncing XML_IMPORT_USER's
XML to the parent directory of 'XML_PATH'. It also contains a module of helper
functions used by the former module.
"""
from djtools.sync.sync_operations import download_music, download_xml, \
                                     upload_music, upload_xml


SYNC_OPERATIONS = {
    'download_music': download_music,
    'download_xml': download_xml,
    'upload_music': upload_music,
    'upload_xml': upload_xml
}
