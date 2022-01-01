"""This module is used to read the genre tags directly from local mp3 files. It
prints the count of tracks within each alphabetized genre and, if verbosity is
increased, also prints the track names.
"""
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


logger = logging.getLogger(__name__)


def get_genres(config):
    """Globs mp3 files on 'USB_PATH', extracts the 'genre' ID3 tags, prints the
    number of tracks in each alphabetized genre, and, if VERBOSITY is
    increased, prints the individual tracks.

    Args:
        config (dict): configuration object

    Raises:
        FileNotFoundError: 'USB_PATH' must exist
    """
    if not os.path.exists(config['USB_PATH']):
        raise FileNotFoundError(f'{config["USB_PATH"]} does not exist!')

    files = set(glob(os.path.join(config['USB_PATH'], 'DJ Music', '**/*.mp3'),
                     recursive=True))
    exclude = set(config['GENRE_EXCLUDE_DIRS'])
    files = [x for x in files if not any((y in x for y in exclude))]

    payload = [files, [config] * len(files)]
    with ThreadPoolExecutor(max_workers=cpu_count() * 4) as executor:
        tracks = [y for x in tqdm(executor.map(get_tag, *payload),
                                  total=len(files)) for y in x]

    for group_id, group in groupby(sorted(tracks, key=itemgetter(0)),
                                   key=itemgetter(0)):
        group = list(group)
        logger.info(f'{group_id}: {len(group)}')
        if config['VERBOSITY'] > 0:
            for track in group:
                logger.info(f'\t{track}')


def get_tag(_file, config):
    """Loads mp3 file and reads the 'genre' ID3 tag field. The genre tag is
    split on 'GENRE_TAG_DELIMITER' and each individual genre tag is zipped with
    the file name.

    Args:
        _file (str): path to mp3 file
        config (dict): configuration object

    Returns:
        list: (genre tag, track title) tuples
    """
    genres = set(map(clean_tag,
                     str(getattr(eyed3.load(_file).tag, 'genre')).split(
                            config['GENRE_TAG_DELIMITER'])))
    track = os.path.basename(_file)

    return list(zip(genres, [track] * len(genres)))


def clean_tag(tag):
    """Removes garbage characters from ID3 genre tag.

    Args:
        tag (str): uncleaned genre tag

    Returns:
        str: genre tag cleaned of garbage characters
    """
    return tag.strip().split(')')[-1].split('\x10')[-1]
