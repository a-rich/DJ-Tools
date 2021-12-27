import logging
import sys
from traceback import format_exc

from config.config import arg_parse, update_config
from src.spotify.playlist_analysis.spotify_analysis import check_playlists
from src.sync.sync_operations import SYNC_OPERATIONS
from src.utils.get_genres import get_genres
from src.utils.randomize_tracks import randomize_tracks
from src.utils.youtube_dl import youtube_dl


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - ' \
                           '%(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('dj_tools')


if __name__ == '__main__':
    try:
        config = update_config(arg_parse())
    except Exception:
        logger.critical(f'Failed to load config: {format_exc()}')
        sys.exit()
    
    if config.get('LOG_LEVEL'):
        logger.setLevel(config['LOG_LEVEL'])
    
    if config.get('RANDOMIZE_TRACKS_PLAYLISTS'):
        randomize_tracks(config)

    if config.get('YOUTUBE_DL_URL'):
        youtube_dl(config)

    if config.get('GET_GENRES'):
        get_genres(config)
    
    if config.get('SPOTIFY_CHECK_PLAYLISTS'):
        check_playlists(config)

    for op in config['SYNC_OPERATIONS']:
        operation = SYNC_OPERATIONS.get(op)
        if not operation:
            logger.warning(f'Invalid operation {op}')
            continue

        try:
            logger.info(f'Beginning {op}...')
            operation(config)
        except:
            logger.warning(f'{op} failed: {format_exc()}')
