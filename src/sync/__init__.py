from src.sync.sync_operations import download_music, download_xml, \
                                     upload_music, upload_xml


SYNC_OPERATIONS = {
    'download_music': download_music,
    'download_xml': download_xml,
    'upload_music': upload_music,
    'upload_xml': upload_xml
}