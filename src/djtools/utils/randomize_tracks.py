"""This module is used to emulate shuffling the track order of one or more
playlists. This is done by setting the Rekordbox tag (i.e. 'TrackNumber') of
tracks in the playlists to sequential numbers. After setting the TrackNumber
tags of tracks in the provided playlists, those playlists must be reimported
for Rekordbox to be aware of the update.
"""
from concurrent.futures import ThreadPoolExecutor
import logging
import os
import random

from bs4 import BeautifulSoup
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

    with open(config['XML_PATH'], 'r', encoding='utf-8') as _file:
        soup = BeautifulSoup(_file.read(), 'xml')

    lookup = {}
    for track in soup.find_all('TRACK'):
        if not track.get('Location'):
            continue
        lookup[track['TrackID']] = track

    playlist_nodes = []
    for playlist in config['RANDOMIZE_TRACKS_PLAYLISTS']:
        try:
            _playlist = get_playlist_track_locations(soup, playlist, lookup)
            tracks = _playlist['tracks']
            playlist_nodes.append(_playlist['playlist'])
        except LookupError as exc:
            logger.error(exc)
            continue

        random.shuffle(tracks)
        payload = [tracks, list(range(len(tracks)))]
        with ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as executor:
            _ = list(tqdm(executor.map(set_tag, *payload),
                          total=len(tracks),
                          desc=f'Randomizing "{playlist}" tracks'))

    wrap_playlists(soup, playlist_nodes)
    _dir, _file = os.path.split(config['XML_PATH'])
    auto_xml_path = os.path.join(_dir, f'auto_{_file}').replace(os.sep, '/')
    with open(auto_xml_path, mode='wb', encoding=soup.orignal_encoding) as \
            _file:
        _file.write(soup.prettify('utf-8'))


def get_playlist_track_locations(soup, _playlist, lookup):
    """Finds playlist in 'XML_PATH' that matches '_playlist' and returns a dict
    of the playlist node and track nodes.

    Args:
        soup (bs4.BeautifulSoup): parsed XML
        _playlist (str): name of playlist to randomize
        lookup (dict): map of TrackIDs to 'Location'

    Raises:
        LookupError: '_playlist' must exist

    Returns:
        dict: playlist node and list of track nodes
    """
    try:
        playlist = soup.find_all('NODE', {'Name': _playlist})[0]
    except IndexError:
        raise LookupError(f'{_playlist} not found') from LookupError

    return {'playlist': playlist,
            'tracks': [lookup[x['Key']] for x in playlist.children
                       if str(x).strip()]}


def set_tag(track, index):
    """Threaded process to set TRACK node's TrackNumber tag.

    Args:
        track (str): TRACK node
        index (int): new TrackNumber
    """
    track['TrackNumber'] = index


def wrap_playlists(soup, playlists):
    """Creates a folder called 'AUTO_RANDOMIZE', inserts the generated playlist
    structure into it, and then inserts 'AUTO_RANDOMIZE' into the root of the
    'Playlist' folder.

    Args:
        soup (bs4.BeautifulSoup): parsed XML
        playlists (bs4.element.Tag): playlist structure
    """
    playlists_root = soup.find_all('NODE', {'Name': 'ROOT', 'Type': '0'})[0]
    new_playlist = soup.new_tag('NODE', Name='AUTO_RANDOMIZE', Type="0")
    for playlist in playlists:
        new_playlist.append(playlist)
    playlists_root.insert(0, new_playlist)
