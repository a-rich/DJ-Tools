"""This module is responsible foor identifying any potential overlap between
tracks in one or more local directory with all the tracks already in the
beatcloud.
"""
from glob import glob
from itertools import groupby
import logging
from operator import itemgetter
import os

from djtools.spotify.playlist_checker import get_beatcloud_tracks, find_matches

logger = logging.getLogger(__name__)


def check_local_dirs(config, beatcloud_tracks=[]):
    """Gets track titles and artists from both local files and beatcloud and 
    computes the Levenshtein similarity between their product in order to
    identify any overlapping tracks.

    Args:
        config (dict): configuration object
    """
    local_tracks = get_local_tracks(config)
    if not local_tracks:
        logger.warning('There are no local tracks; make sure ' \
                       'LOCAL_CHECK_DIRS has one or more directories ' \
                       '(under "DJ Music") containing one or more tracks')
        return
    if not beatcloud_tracks:
        beatcloud_tracks = get_beatcloud_tracks()
    matches = find_matches(local_tracks, beatcloud_tracks, config)
    logger.info(f'Local tracks / beatcloud matches: {len(matches)}')
    for playlist, matches in groupby(sorted(matches, key=itemgetter(0)),
                                     key=itemgetter(0)):
        logger.info(f'{playlist}:')
        for _, spotify_track, beatcloud_track, fuzz_ratio in matches:
            logger.info(f'\t{fuzz_ratio}: {spotify_track} | {beatcloud_track}')
    
    return beatcloud_tracks


def get_local_tracks(config):
    """Aggregates the files from one or more local directories in a dictionary
    mapped with parent directories.

    Args:
        config (dict): configuration object 

    Raises:
        KeyError: 'LOCAL_CHECK_DIRS' and 'USB_PATH' must be configured

    Returns:
        dict: local file names keyed by parent directory
    """
    if not config.get('LOCAL_CHECK_DIRS') or not config.get('USB_PATH'):
        raise KeyError('Using the local_dirs_checker module requires the ' \
                       'config option LOCAL_CHECK_DIRS to be set to a list ' \
                       'of one or more directories (under "DJ Music") ' \
                       'containing new tracks and USB_PATH to be set to a ' \
                       'drive containing the "DJ Music" directory')

    local_dir_tracks = {}
    for _dir in config['LOCAL_CHECK_DIRS']:
        path = os.path.join(config['USB_PATH'], 'DJ Music', 
                            _dir).replace(os.sep, '/')
        if not os.path.exists(path):
            logger.warning(f'{path} does not exist; will not be able to ' \
                           'check its contents against the beatcloud')
            continue
        files = glob(os.path.join(path, '**', '*.*').replace(os.sep, '/'),
                     recursive=True)
        if not files:
            continue
        local_dir_tracks[_dir] = [os.path.splitext(os.path.basename(x))[0]
                                  for x in files]

    return local_dir_tracks
