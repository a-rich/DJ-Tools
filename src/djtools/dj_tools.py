"""This is the entry point for the DJ Tools library.

Spotify operations:
    * SPOTIFY_CHECK_PLAYLISTS (playlist_checker.py): identify overlap between
            Spotify playlist(s) and beatcloud
    * AUTO_PLAYLIST_UPDATE (playlist_builder.py): creating and updating Spotify
            playlists using subreddit top posts

Utils operations:
    * GENERATE_GENRE_PLAYLISTS (generate_genre_playlists.py): automatically
            create a desired playlist structure based on the genre ID3 tags
            present in an XML
    * GET_GENRES (get_genres.py): display track counts for all genres using the
            ID3 tag field of local mp3 files
    * RANDOMIZE_TRACKS (randomize_tracks.py): set ID3 tags of tracks in
            playlists sequentially (after shuffling) to randomize
    * YOUTUBE_DL (youtube_dl.py): download tracks from a URL (e.g. Soundcloud
            playlist)

Sync operations:
    * SYNC_OPERATIONS (sync_operations.py)
        - download_music: sync tracks from beatcloud to USB_PATH
        - download_xml: sync XML_IMPORT_USER's beatcloud XML to
                XML_PATH's parent folder
        - upload_music: sync tracks from USB_PATH to beatcloud
        - upload_xml: sync XML_PATH to USER's beatcloud XML folder
"""
from datetime import datetime
import logging
import logging.config
import os
from traceback import format_exc

from djtools.spotify import SPOTIFY_OPERATIONS
from djtools.sync import SYNC_OPERATIONS
from djtools.utils import UTILS_OPERATIONS
from djtools.utils.config import build_config
from djtools.utils.helpers import upload_log


# initialize logger
log_file = os.path.join(os.path.dirname(__file__), 'logs',
                        f"{datetime.now().strftime('%Y-%m-%d')}.log")
logging.config.fileConfig(fname=os.path.join(os.path.dirname(__file__),
                                             'configs', 'logging.conf'),
                          defaults={'logfilename': log_file},
                          disable_existing_loggers=False)
logger = logging.getLogger(__name__)

# load 'config.json', override with any command-line arguments, and
# validate the final config
try:
    config = build_config()
    if config.get('LOG_LEVEL'):
        logger.setLevel(config['LOG_LEVEL'])
except Exception as exc:
    msg = f'Failed to load config: {exc}\n{format_exc()}'
    logger.critical(msg)
    raise ValueError(msg) from Exception


def main():
    """This is the entry point for the DJ Tools library.
    """
    # run 'spotify' package and 'utils' package operations if any of the flags
    # to do so are present in the config
    for operation, func in {**SPOTIFY_OPERATIONS, **UTILS_OPERATIONS}.items():
        if not config.get(operation):
            continue
        try:
            logger.info(f'Beginning {operation}...')
            func(config)
        except Exception as exc:
            logger.error(f'{operation} failed: {exc}\n{format_exc()}')

    # run 'sync' package operations if any of the options to do so are present
    # in the 'SYNC_OPERATIONS' config option
    for operation in config['SYNC_OPERATIONS']:
        func = SYNC_OPERATIONS.get(operation)
        if not func:
            logger.warning(f'Invalid sync operation "{operation}"')
            continue

        try:
            logger.info(f'Beginning {operation}...')
            func(config)
        except Exception as exc:
            logger.error(f'{operation} failed: {exc}\n{format_exc()}')

    # attempt uploading today's log file
    try:
        upload_log(config, log_file)
    except Exception:
        logger.error(f'Unable to upload log "{log_file}":\n{format_exc()}')


if __name__ == '__main__':
    main()
