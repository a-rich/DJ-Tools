"""The 'sync' package contains a module for syncing tracks to and from the
beatcloud, syncing the current user's rekordbox.xml to the beatcloud, and
syncing other users' rekordbox.xml to the parent directory of 'XML_PATH'. It
also contains a module of helper functions used by the former module.
"""
from src.sync.sync_operations import download_music, download_xml, \
                                     upload_music, upload_xml


SYNC_OPERATIONS = {
    'download_music': download_music,
    'download_xml': download_xml,
    'upload_music': upload_music,
    'upload_xml': upload_xml
}