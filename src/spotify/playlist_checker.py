from concurrent.futures import ThreadPoolExecutor
from itertools import groupby, product
import json
import logging
from operator import itemgetter
import os

from dateutil.parser import parse
from fuzzywuzzy import fuzz
import Levenshtein
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tqdm import tqdm


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - ' \
                           '%(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('spotify_analysis')


def check_playlists(config):
    spotify_tracks = get_spotify_tracks(config)
    beatcloud_tracks = get_beatcloud_tracks()
    matches = find_matches(spotify_tracks, beatcloud_tracks, config)

    logger.info(f'Spotify playlist(s) / beatcloud matches: {len(matches)}')
    for playlist, matches in groupby(sorted(matches, key=itemgetter(0)),
                                     key=itemgetter(0)):
        logger.info(f'{playlist}:')
        for _, spotify_track, beatcloud_track, fuzz_ratio in matches:
            logger.info(f'\t{fuzz_ratio}: {spotify_track} | {beatcloud_track}')


def get_spotify_tracks(config):
    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=config['SPOTIFY_CLIENT_ID'], 
            client_secret=config['SPOTIFY_CLIENT_SECRET'], 
            redirect_uri=config['SPOTIFY_REDIRECT_URI'], 
            scope='playlist-modify-public'))
    playlist_ids = {key.lower(): value for key, value in json.load(
            open(os.path.join('config', 'playlist_checker.json'))).items()}
    playlist_tracks = {}
    for playlist in config["SPOTIFY_PLAYLISTS_CHECK"]:
        playlist_id = playlist_ids.get(playlist.lower())
        if not playlist_id:
            logger.error(f'{playlist} not in playlist_checker.json')
            continue

        logger.info(f'Getting tracks from Spotify playlist "{playlist}"...')
        playlist_tracks[playlist] = get_playlist_tracks(spotify, playlist_id)
        logger.info(f'Got {len(playlist_tracks[playlist])} tracks')

        if config['VERBOSITY'] > 0:
            for track in playlist_tracks[playlist]:
                logger.info(f'\t{track}')

    return playlist_tracks


def get_playlist_tracks(spotify, playlist_id):
    try:
        playlist = spotify.playlist(playlist_id)
    except Exception:
        raise Exception(f"Failed to get playlist with ID {playlist_id}")

    result = playlist['tracks']
    tracks = add_tracks(result)

    while result['next']:
        result = spotify.next(result)
        tracks.extend(add_tracks(result))

    return set(tracks)


def add_tracks(result):
    tracks = []
    for track in result['items']:
        title = track['track']['name']
        artists = ', '.join([y['name'] for y in track['track']['artists']])
        tracks.append(f'{title} - {artists}')
    
    return tracks


def get_beatcloud_tracks():
    logger.info('Getting tracks from the beatcloud...')
    cmd = 'aws s3 ls --recursive s3://dj.beatcloud.com/dj/music/'
    with os.popen(cmd) as proc:
        output = proc.read().split('\n')
    tracks = [os.path.splitext(os.path.basename(track))[0]
              for track in output if track]
    logger.info(f'Got {len(tracks)} tracks')

    return tracks


def find_matches(spotify_tracks, beatcloud_tracks, config):
    spotify_tracks = [(playlist, track)
                      for playlist, tracks in spotify_tracks.items()
                      for track in tracks]
    _product = list(product(spotify_tracks, beatcloud_tracks))
    _temp, beatcloud_tracks = zip(*_product)
    spotify_playlists, spotify_tracks = zip(*_temp)
    payload = [spotify_playlists, spotify_tracks, beatcloud_tracks,
               [config['SPOTIFY_PLAYLISTS_CHECK_FUZZ_RATIO']] * len(_product)]
    with ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as executor:
        matches = list(filter(None, tqdm(executor.map(compute_distance,
                                                      *payload),
                                         total=len(_product),
                                         desc='Matching Spotify and Beatcloud tracks')))
    
    return matches


def compute_distance(spotify_playlist, spotify_track, beatcloud_track,
                     threshold):
    fuzz_ratio = fuzz.ratio(spotify_track, beatcloud_track)
    if fuzz_ratio >= threshold:
        return spotify_playlist, spotify_track, beatcloud_track, fuzz_ratio
