from argparse import ArgumentParser
from datetime import datetime
from glob import glob
import json
import logging
import os
from urllib.parse import quote, unquote

from bs4 import BeautifulSoup
import eyed3
eyed3.log.setLevel("ERROR")
from fuzzywuzzy import fuzz
from tqdm import tqdm


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - ' \
                           '%(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('swap_title_artist')


def get_bad_tracks():
    files = glob('/Volumes/AWEEEEZY/DJ Music/**/*.mp3', recursive=True)
    bad_tracks = []
    for _file in files:
        if 'Tarek' in _file or os.path.basename(_file) in IGNORE_TRACKS:
            continue

        file_title = os.path.basename(_file).split(' - ')[0]
        tag_title = getattr(eyed3.load(_file).tag, 'title')
        fuzz_ratio = fuzz.ratio(file_title.lower().strip(), tag_title.lower().strip())
        if fuzz_ratio < args.fuzz_ratio and tag_title not in file_title and file_title not in tag_title:
            logger.info(f'{os.path.basename(_file)}: {file_title} vs. {tag_title} = {fuzz_ratio}')
            bad_tracks.append(_file)

    logger.info(f'{len(bad_tracks)} bad tracks')

    return bad_tracks


def replace_tracks(tracks):
    s3_prefix = 's3://dj.beatcloud.com/dj/music/'
    for track in tracks:
        dir = os.path.dirname(track)
        base_name = os.path.basename(track)
        sub_dir = os.path.basename(dir)
        name, ext = os.path.splitext(base_name)
        artist, title = name.split(' - ')
        new_base_name = ' - '.join([title, artist]) + ext
        new_name = os.path.join(dir, new_base_name)
        cp_cmd = f'aws s3 cp "{new_name}" "{os.path.join(s3_prefix, sub_dir, new_base_name)}"'
        rm_cmd = f'aws s3 rm "{os.path.join(s3_prefix, sub_dir, base_name)}"'
        os.rename(track, new_name)
        # NOTE: no need to upload files one-by-one since `dj_tools.py --upload_music` does so in parallel
        # os.system(cp_cmd)
        os.system(rm_cmd)


def get_playlist_track_locations(soup, _playlist, lookup):
    try:
        playlist = soup.find_all('NODE', {'Name': _playlist})[0]
    except IndexError:
        raise LookupError(f'{_playlist} not found')
    
    return [lookup[x['Key']] for x in playlist.children if str(x).strip()]


def fix_track_location(xml_path, playlist):
    soup = BeautifulSoup(open(xml_path, 'r').read(), 'xml')
    lookup = {x['TrackID']: x
              for x in soup.find_all('TRACK') if x.get('Location')}

    try:
        tracks = get_playlist_track_locations(soup, playlist, lookup)
    except LookupError as e:
        logger.error(e)
    
    logger.info(f'{len(tracks)} tracks to repair in playlist "{playlist}"')
    for track in tracks:
        loc = track['Location']
        dir_name = os.path.dirname(loc)
        base_name = unquote(os.path.basename(loc))
        base_name, ext = os.path.splitext(base_name)
        artist, title = base_name.split(' - ')
        new_base_name = quote(' - '.join([title, artist]) + ext)
        track['Location'] = os.path.join(dir_name, new_base_name)
        logger.info(f'{unquote(loc)} -> {unquote(os.path.join(dir_name, new_base_name))}')

    with open(xml_path, mode='wb',
              encoding=soup.orignal_encoding) as f:
        f.write(soup.prettify('utf-8'))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--fuzz_ratio', type=int, default=0,
            help='threshold dissimilarity between ID3 title tag and ' \
                 'supposed title from file name')
    parser.add_argument('--replace', action='store_true',
            help='flag to perform file renaming and S3 delete (follow up ' \
                 'with dj_tools upload_music)')
    parser.add_argument('--xml_path', type=str,
            help='path to "rekordbox.xml" file')
    parser.add_argument('--xml_swap_playlist', type=str,
            help='playlist name in which all tracks should have the ' \
                 'title/artist swap performed on their location')
    args = parser.parse_args()

    IGNORE_TRACKS = set([
        "Scratch Sentence 5.mp3",
        "Scratch Sentence 1.mp3"
    ])

    if args.fuzz_ratio:
        bad_tracks = get_bad_tracks()

        if args.replace:
            json.dump(bad_tracks, 
                    open(os.path.join('bad_tracks', 
                                        f'{datetime.now().timestamp()}.json'),
                        'w'))
            replace_tracks(bad_tracks)
    
    if args.xml_swap_playlist:
        fix_track_location(args.xml_path, args.xml_swap_playlist)
