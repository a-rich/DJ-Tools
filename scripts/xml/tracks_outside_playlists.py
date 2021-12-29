from argparse import ArgumentParser
import logging

from bs4 import BeautifulSoup
from bs4.element import Tag


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - ' \
                           '%(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('tracks_outside_playlists')


def get_tracks(soup, name, folder):
    tracks = {x['TrackID']: x
              for x in soup.find_all('TRACK') if x.get('Location')}
    node = soup.find_all('NODE', {'Name': name, 'Type': '0' if folder else '1'})[0]
    if folder:
        playlists = node.find_all('NODE', {'Type': '1'}) 
    else:
        playlists = [node]

    logger.info(f'Tracks: {len(tracks)}')
    logger.info(f'Playlists: {len(playlists)}')

    for playlist in playlists:
        for track in playlist.children:
            if not (isinstance(track, Tag) and tracks.get(track['Key'])): 
                continue
            del tracks[track['Key']]

    logger.info(f'Dangling tracks: {len(tracks)}')

    return tracks


def create_playlist(soup, tracks, new_playlist):
    playlists_root = soup.find_all('NODE', {'Name': 'ROOT', 'Type': '0'})[0]
    new_playlist = soup.new_tag('NODE', Name=new_playlist, Type="1",
                                KeyType="0", Entries=str(len(tracks)))
    playlists_root.insert(0, new_playlist)    
    for track_id, track in tracks.items():
        new_playlist.append(soup.new_tag('TRACK', Key=track_id))
        

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--xml_path', required=True, type=str,
                        help='path to "rekordbox.xml"')
    parser.add_argument('--name', type=str, required=True,
                        help='playlist / folder used to find missing tracks')
    parser.add_argument('--folder', action='store_true',
                        help='set if "--name" is folder instead of playlist')
    parser.add_argument('--new_xml_path', type=str,
                        default='new_rekordbox.xml',
                        help='path to new "rekordbox.xml"')
    parser.add_argument('--new_playlist', type=str, default='Dangling Tracks',
                        help='name of playlist to create')
    
    args = parser.parse_args()

    soup = BeautifulSoup(open(args.xml_path).read(), 'xml')
    create_playlist(soup, get_tracks(soup, args.name, args.folder),
                    args.new_playlist)

    with open(args.new_xml_path, mode='wb',
              encoding=soup.orignal_encoding) as f:
        f.write(soup.prettify('utf-8'))
