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
