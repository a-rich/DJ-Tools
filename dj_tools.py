"""This is the entry point for the DJ Tools library.

Spotify operations:
    * CHECK_PLAYLIST (playlist_checker.py): identify overlap between Spotify
            playlist(s) and beatcloud
    * UPDATE_AUTO_PLAYLISTS (playlist_builder.py): creating and updating
            Spotify playlists using subreddit top posts

Utils operations:
    * GENERATE_GENRE_PLAYLISTS (generate_genre_playlists.py): automatically
            create a desired playlist structure based on the genre ID3 tags
            present in an XML
    * GET_GENRES (get_genres.py): display track counts for all genres using the
            ID3 tag field of local mp3 files
    * RANDOMIZE_TRACKS (randomize_tracks.py): set the track_num ID3 tags of
            tracks in playlists sequentially (after shuffling) to randomize
    * YOUTUBE_DL (youtube_dl.py): download tracks from a URL (e.g. Soundcloud
            playlist)

Sync operations:
    * SYNC_OPERATIONS (sync_operations.py)
        - download_music: sync tracks from beatcloud to USB
        - download_xml: sync XML_IMPORT_USER's beatcloud rekordbox.xml to USB
        - upload_music: sync tracks from USB to beatcloud
        - upload_xml: sync rekordbox.xml to beatcloud
"""
import logging
import sys
from traceback import format_exc

from config.config import arg_parse, update_config
from src.spotify import SPOTIFY_OPERATIONS
from src.sync import SYNC_OPERATIONS
from src.utils import UTILS_OPERATIONS


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - ' \
                           '%(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('dj_tools')


if __name__ == '__main__':
    try:
        config = update_config(arg_parse())
        if config.get('LOG_LEVEL'):
            logger.setLevel(config['LOG_LEVEL'])
    except Exception as e:
        logger.critical(f'Failed to load config: {e}\n{format_exc()}')
        sys.exit()
    
    for op, func in {**SPOTIFY_OPERATIONS, **UTILS_OPERATIONS}.items():
        if not config.get(op):
            continue
        try:
            logger.info(f'Beginning {op}...')
            func(config)
        except Exception as e:
            logger.error(f'{op} failed: {e}\n{format_exc()}')
    
    for op in config['SYNC_OPERATIONS']:
        func = SYNC_OPERATIONS.get(op)
        if not func:
            logger.warning(f'Invalid sync operation "{op}"')
            continue

        try:
            logger.info(f'Beginning {op}...')
            func(config)
        except Exception as e:
            logger.error(f'{op} failed: {e}\n{format_exc()}')
