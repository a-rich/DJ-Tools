"""This module is used to emulate shuffling the track order of one or more
playlists. This is done by setting the ID3 tag (e.g. 'track_num') of tracks in
the playlists to sequential numbers. After setting track ID3 tags, those tracks
must have their tags reloaded (Select > right-click > Reload Tags).
"""
from concurrent.futures import ThreadPoolExecutor
import logging
import os
import random
from urllib.parse import unquote

from bs4 import BeautifulSoup
import eyed3
eyed3.log.setLevel("ERROR")
from tqdm import tqdm


logger = logging.getLogger(__name__)


def randomize_tracks(config):
    """For each playlist in 'RANDOMIZE_TRACKS_PLAYLISTS', shuffle the tracks
    and sequentially set the 'RANDOMIZE_TRACKS_TAG' ID3 tag to a number to
    emulate track randomization.

    Args:
        config (dict): configuration object

    Raises:
        FileNotFoundError: 'USB_PATH' must exist
        FileNotFoundError: 'XML_PATH' must exist
    """
    if not os.path.exists(config['USB_PATH']):
        raise FileNotFoundError(f'{config["USB_PATH"]} does not exist!')

    if not os.path.exists(config['XML_PATH']):
        raise FileNotFoundError(f'{config["XML_PATH"]} does not exist!')

    soup = BeautifulSoup(open(config['XML_PATH'], 'r',
                              encoding='utf-8').read(), 'xml')
    lookup = {x['TrackID']: unquote(x['Location'].replace(
              'file://localhost', ''))
              for x in soup.find_all('TRACK') if x.get('Location')}

    for playlist in config['RANDOMIZE_TRACKS_PLAYLISTS']:
        try:
            tracks = get_playlist_track_locations(soup, playlist, lookup)
        except LookupError as exc:
            logger.error(exc)
            continue

        random.shuffle(tracks)
        payload = [tracks,
                   [config['RANDOMIZE_TRACKS_TAG']] * len(tracks),
                   list(range(len(tracks)))]
        with ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as executor:
            _ = list(tqdm(executor.map(set_tag, *payload),
                          total=len(tracks),
                          desc=f'Randomizing "{playlist}" tracks'))


def get_playlist_track_locations(soup, _playlist, lookup):
    """Finds playlist in 'XML_PATH' that matches '_playlist' and returns a list
    of track 'Location' fields.

    Args:
        soup (bs4.BeautifulSoup): parsed XML
        _playlist (str): name of playlist to randomize
        lookup (dict): map of TrackIDs to 'Location'

    Raises:
        LookupError: '_playlist' must exist

    Returns:
        list: track 'Location' fields
    """
    try:
        playlist = soup.find_all('NODE', {'Name': _playlist})[0]
    except IndexError:
        raise LookupError(f'{_playlist} not found') from LookupError

    return [lookup[x['Key']] for x in playlist.children if str(x).strip()]


def set_tag(track, tag, index):
    """Loads mp3 file with eyed3 package and sets its 'tag' ID3 tag with
    'index' to emulate randomization.

    Args:
        track (str): path to mp3 file
        tag (str): ID3 tag to set
        index (int): [description]
    """
    track = eyed3.load(track)
    setattr(track.tag, tag, index)
    track.tag.save()
