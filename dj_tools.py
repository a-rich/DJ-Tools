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
import sys
from traceback import format_exc

from src.spotify import SPOTIFY_OPERATIONS
from src.sync import SYNC_OPERATIONS
from src.utils import UTILS_OPERATIONS
from src.utils.config import arg_parse, update_config
from src.utils.helpers import upload_log


os.makedirs('logs', exist_ok=True)
LOG_FILE = os.path.join('logs', f"{datetime.now().strftime('%Y-%m-%d')}.log")
logging.config.fileConfig(fname=os.path.join('config', 'logging.conf'),
        defaults={'logfilename': LOG_FILE},
        disable_existing_loggers=False)
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    # load 'config.json', override with any command-line arguments, and
    # validate the final config
    try:
        config = update_config(arg_parse())
        if config.get('LOG_LEVEL'):
            logger.setLevel(config['LOG_LEVEL'])
    except Exception as exc:
        logger.critical(f'Failed to load config: {exc}\n{format_exc()}')
        try:
            upload_log(config, LOG_FILE)
        except Exception:
            logger.error(f'Unable to upload log "{LOG_FILE}":\n{format_exc()}')
        sys.exit()

    # run 'spotify' package and 'utils' package operations if any of the flags
    # to do so are present in the config
    for op, func in {**SPOTIFY_OPERATIONS, **UTILS_OPERATIONS}.items():
        if not config.get(op):
            continue
        try:
            logger.info(f'Beginning {op}...')
            func(config)
        except Exception as exc:
            logger.error(f'{op} failed: {exc}\n{format_exc()}')

    # run 'sync' package operations if any of the options to do so are present
    # in the 'SYNC_OPERATIONS' config option
    for op in config['SYNC_OPERATIONS']:
        func = SYNC_OPERATIONS.get(op)
        if not func:
            logger.warning(f'Invalid sync operation "{op}"')
            continue

        try:
            logger.info(f'Beginning {op}...')
            func(config)
        except Exception as exc:
            logger.error(f'{op} failed: {exc}\n{format_exc()}')

    # attempt uploading today's log file
    try:
        upload_log(config, LOG_FILE)
    except Exception:
        logger.error(f'Unable to upload log "{LOG_FILE}":\n{format_exc()}')
