from argparse import ArgumentParser
import json
import logging
import os

from bs4 import BeautifulSoup
from bs4.element import Tag


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - ' \
                           '%(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('generate_playlists')


def generate_genre_playlists(config):
    if not os.path.exists(config['XML_PATH']):
        raise FileNotFoundError(f'{config["XML_PATH"]} does not exist!')

    soup = BeautifulSoup(open(config['XML_PATH']).read(), 'xml')
    tracks = get_track_genres(soup, config['GENRE_TAG_DELIMITER'])
    struct = json.load(open(os.path.join('config',
                                         'generate_genre_playlists.json')))
    genres = set()
    playlists = create_playlists(soup, struct, genres)

    if config['GENERATE_GENRE_PLAYLISTS_REMAINDER']:
        add_other(soup, config['GENERATE_GENRE_PLAYLISTS_REMAINDER'], genres,
                  tracks, playlists)
    
    add_tracks(soup, playlists, tracks)
    wrap_playlists(soup, playlists)

    _dir, _file = os.path.split(config['XML_PATH'])
    auto_xml_path = os.path.join(_dir, f'auto_{_file}')
    with open(auto_xml_path, mode='wb', encoding=soup.orignal_encoding) as f:
        f.write(soup.prettify('utf-8'))


def get_track_genres(soup, delimiter):
    tracks = {}
    for track in soup.find_all('TRACK'):
        if not track.get('Location'):
            continue
        track_genres = [x.strip() for x in track['Genre'].split(delimiter)]
        for genre in track_genres:
            if genre in tracks:
                tracks[genre].append(track['TrackID'])
            else:
                tracks[genre] = [track['TrackID']]

    return tracks


def create_playlists(soup, content, genres):
    if isinstance(content, dict):
        content = {k.lower(): v for k, v in content.items()}
        folder = soup.new_tag('NODE', Name=content['name'], Type="0")
        if content['name'] != 'Genres':
            _all = soup.new_tag('NODE', KeyType="0",
                                Name=f'All {content["name"]}', Type="1")
            folder.append(_all)
        for playlist in content['playlists']:
            folder.append(create_playlists(soup, playlist, genres))
        return folder
    elif isinstance(content, str):
        genres.add(content)
        playlist = soup.new_tag('NODE', KeyType="0", Name=content, Type="1")
        return playlist
    else:
        raise ValueError('Encountered invalid input type ' \
                         f"{type(content)}: {content}")


def add_other(soup, remainder_type, genres, tracks, playlists):
    if remainder_type == 'folder':
        folder = soup.new_tag('NODE', Name='Other', Type='0')
        for other in set(tracks).difference(genres):
            playlist = soup.new_tag('NODE', Name=other, Type="1", KeyType="0")
            folder.append(playlist)
        playlists.append(folder)
    elif remainder_type == 'playlist':
        playlist = soup.new_tag('NODE', Name='Other', Type="1", KeyType="0")
        playlists.append(playlist)
    else:
        logger.error(f'Invalid remainder type "{remainder_type}"')


def add_tracks(soup, playlists, tracks):
    seen = {}
    for playlist in playlists.find_all('NODE', {'Type': '1'}):
        if playlist['Name'] not in seen:
            seen[playlist['Name']] = set()

        for track in tracks.get(playlist['Name'], []):
            track_tag = soup.new_tag('TRACK', Key=track)
            if track not in seen[playlist['Name']]:
                playlist.append(track_tag)
                seen[playlist['Name']].add(track)

            parent = playlist.parent
            while parent:
                try:
                    _all = parent.find_all('NODE', 
                                           {'Name': f'All {parent["Name"]}'},
                                           recursive=False)[0]
                    if _all['Name'] not in seen:
                        seen[_all['Name']] = set()

                    track_tag = soup.new_tag('TRACK', Key=track)
                    if track not in seen[_all['Name']]:
                        _all.append(track_tag)
                        seen[_all['Name']].add(track)
                except IndexError:
                    break
                parent = parent.parent


def wrap_playlists(soup, playlists):
    playlists_root = soup.find_all('NODE', {'Name': 'ROOT', 'Type': '0'})[0]
    new_playlist = soup.new_tag('NODE', Name='AUTO_GENRES', Type="0")
    new_playlist.insert(0, playlists)
    playlists_root.insert(0, new_playlist)    
