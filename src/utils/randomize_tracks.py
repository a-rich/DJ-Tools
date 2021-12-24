from concurrent.futures import ThreadPoolExecutor
import logging
from os import cpu_count
import random
from threading import Thread
from urllib.parse import unquote

from bs4 import BeautifulSoup
import eyed3
from tqdm import tqdm


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('randomize_tracks')
        

def set_tag(track, config, index):
    track = eyed3.load(track)
    setattr(track.tag, config['RANDOMIZE_TRACKS_TAG'], index)
    track.tag.save()


def randomize_tracks(config):
    soup = BeautifulSoup(open(config['XML_PATH'], 'r').read(), 'lxml')
    lookup = {x['trackid']: unquote(x['location'].replace(
              'file://localhost', ''))
              for x in soup.find_all('track') if x.get('location')}

    for playlist in config['RANDOMIZE_TRACKS_PLAYLISTS']:
        try:
            tracks = get_playlist_track_locations(soup, playlist, lookup)
        except LookupError as e:
            logger.error(e)
            continue

        random.shuffle(tracks)
        payload = [tracks, [config] * len(tracks), list(range(len(tracks)))]
        with ThreadPoolExecutor(max_workers=cpu_count() * 4) as executor: 
            [x for x in tqdm(executor.map(set_tag, *payload),
                             total=len(tracks),
                             desc=f'Randomizing "{playlist}" tracks')]


def get_playlist_track_locations(soup, _playlist, lookup):
    try:
        playlist = soup.find_all('node', {'name': _playlist})[0]
    except StopIteration:
        raise LookupError(f'{_playlist} not found')
    
    return [lookup[x['key']] for x in playlist.children if str(x).strip()]
