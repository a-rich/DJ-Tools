import logging
import random

from bs4 import BeautifulSoup
import eyed3


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('randomize_tracks')


def randomize_tracks(config):
    soup = BeautifulSoup(open(config['XML_PATH'], 'r').read(), 'lxml')
    for playlist in config['RANDOMIZE_TRACKS_PLAYLISTS']:
        try:
            tracks = get_playlist_track_locations(soup, playlist)
        except LookupError as e:
            logger.error(e)
            continue

        random.shuffle(tracks)
        #TODO: parallelize
        for index, track in enumerate(tracks):
            track = eyed3.load(track)
            setattr(track.tag, config['RANDOMIZE_TRACKS_TAG'], index)
            track.tag.save()


def get_playlist_track_locations(soup, _playlist):
    try:
        playlist = next(iter(soup.find_all('node', {'name': _playlist})))
    except StopIteration:
        raise LookupError(f'{_playlist} not found')
    
    tracks = [x for x in playlist.children if str(x).strip()]
    tracks = [next(iter(x.get_attribute_list('key'))) for x in tracks]
    tracks = [next(iter(soup.findAll('track', {"trackid": x})))
              for x in tracks]
    tracks = [next(iter(x.get_attribute_list('location'))) for x in tracks]
    tracks = [x.replace('file://localhost', '').replace('%20', ' ')
              for x in tracks]

    return tracks 
