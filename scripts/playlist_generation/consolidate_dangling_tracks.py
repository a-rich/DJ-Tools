from argparse import ArgumentParser
import logging

from bs4 import BeautifulSoup
from bs4.element import Tag


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - ' \
                           '%(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('parser')


def get_dangling_tracks(soup):
    tracks = {x['TrackID']: x
              for x in soup.find_all('TRACK') if x.get('Location')}
    genre_folder = soup.find_all('NODE', {'Name': 'Genres', 'Type': '0'})[0]
    genre_playlists = genre_folder.find_all('NODE', {'Type': '1'}) 
    logger.info(f'Tracks: {len(tracks)}')
    logger.info(f'Genre playlists: {len(genre_playlists)}')

    for playlist in genre_playlists:
        for track in playlist.children:
            if not (isinstance(track, Tag) and tracks.get(track['Key'])): 
                continue
            del tracks[track['Key']]

    logger.info(f'Dangling tracks: {len(tracks)}')

    return tracks


def create_dangling_tracks_playlist(soup, tracks, playlist_name):
    playlists_root = soup.find_all('NODE', {'Name': 'ROOT', 'Type': '0'})[0]
    new_playlist = soup.new_tag('NODE', Name=playlist_name, Type="1",
                                KeyType="0", Entries=str(len(tracks)))
    playlists_root.insert(0, new_playlist)    
    for track_id, track in tracks.items():
        new_playlist.append(soup.new_tag('TRACK', Key=track_id))
        

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--xml_path', type=str, help='path to "rekordbox.xml"')
    parser.add_argument('--xml_write_path', type=str,
                        help='path to new "rekordbox.xml"')
    parser.add_argument('--playlist_name', type=str, default='Dangling Tracks',
                        help='name of playlist to create')
    args = parser.parse_args()

    soup = BeautifulSoup(open(args.xml_path).read(), 'xml')
    create_dangling_tracks_playlist(soup, get_dangling_tracks(soup),
                                    args.playlist_name)

    with open(args.xml_write_path, mode='wb',
              encoding=soup.orignal_encoding) as f:
        f.write(soup.prettify('utf-8'))
