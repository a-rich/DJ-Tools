from concurrent.futures import ThreadPoolExecutor
from glob import glob
from itertools import groupby
import logging
from multiprocessing import cpu_count
from operator import itemgetter
import os

import eyed3
eyed3.log.setLevel("ERROR")
from tqdm import tqdm


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('get_genres')


def clean_tag(tag):
    return tag.strip().split(')')[-1].split('\x10')[-1]

def get_tag(x, config):
    genres = set(map(clean_tag, 
                     str(getattr(eyed3.load(x).tag, 'genre')).split(
                            config['GENRE_TAG_DELIMITER'])))
    track = os.path.basename(x)

    return list(zip(genres, [track] * len(genres)))


def get_genres(config):
    files = set(glob(os.path.join(config['USB_PATH'], 'DJ Music', '**/*.mp3'),
                     recursive=True))
    exclude = set(config['GENRE_EXCLUDE_DIRS'])
    files = [x for x in files if not any([y in x for y in exclude])]
    
    payload = [files, [config] * len(files)]
    with ThreadPoolExecutor(max_workers=cpu_count() * 4) as executor:
        tracks = [y for x in tqdm(executor.map(get_tag, *payload),
                                  total=len(files)) for y in x]

    for group_id, group in groupby(sorted(tracks, key=itemgetter(0)),
                                   key=itemgetter(0)):
        group = list(group)
        logger.info(f'{group_id}: {len(group)}')
        if config.get('GENRE_VERBOSE'):
            for track in group:
                logger.info(f'\t{track}')
