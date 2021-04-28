from spotipy.oauth2 import SpotifyClientCredentials
from itertools import combinations, product
from argparse import ArgumentParser
from datetime import datetime
from itertools import groupby
from fuzzywuzzy import fuzz
from dateutil import parser
from pathlib import Path
from glob import glob
from tqdm import tqdm
import spotipy
import json
import os



try:
    import Levenshtein
except:
    print(f"[WARNING]: you can get a huge speed boost fuzzy matching local files if you run `pip install python-Levenshtein`")

p = ArgumentParser()
p.add_argument('--playlist_data', type=str, default='playlist_data.json',
        help='path to playlist JSON')
p.add_argument('--compare_playlists', nargs='+',
        help='list of Spotify Playlist IDs to compare for track overlap')
p.add_argument('--compare_local', type=str,
        help='path to root of DJ USB')
p.add_argument('--new', type=parser.parse,
        help='datetime after which songs are considered new')
p.add_argument('--fuzz_ratio', type=int, default=87,
        help='lower-bound similarity between Spotify and local tracks to consider a match')
p.add_argument('--verbose', action='store_true',
        help='verbosity level')
args = p.parse_args()


def get_tracks(playlist_id):
    try:
        playlist = spotify.playlist(playlist_id)
    except Exception as e:
        raise Exception(f"failed to get playlist with ID {playlist_id}")
    
    tracks = playlist['tracks']
    result = []

    while tracks['next']:
        result.extend([f"{x['track']['name']} - {', '.join([y['name'] for y in x['track']['artists']])}.mp3"
                for x in tracks['items']])
        tracks = spotify.next(tracks)

    result.extend([f"{x['track']['name']} - {', '.join([y['name'] for y in x['track']['artists']])}.mp3"
                for x in tracks['items']])

    return result


spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
playlists = json.load(open(args.playlist_data, 'r'))
tracks_by_playlist = {}

print(f"Getting track data from Spotify...")
for playlist in args.compare_playlists:
    if playlist.lower() == 'all':
        for playlist in playlists:
            try:
                tracks_by_playlist[playlist] = get_tracks(playlists.get(playlist.lower(), playlist))
            except Exception as e:
                print(f"failed to get playlist {playlist}: {e}")
        break
    else:
        try:
            tracks_by_playlist[playlist] = get_tracks(playlists.get(playlist.lower(), playlist))
        except Exception as e:
            print(f"failed to get playlist {playlist}: {e}")
            continue

print(f"\nComparing Spotify playlists with each other...")
for a,b in combinations(tracks_by_playlist, 2):
    intersection = set(tracks_by_playlist[a]).intersection(set(tracks_by_playlist[b]))
    if intersection:
        left = f"{a.title()} ({len(tracks_by_playlist[a])})"
        right = f"{b.title()} ({len(tracks_by_playlist[b])})"
        print(f"{left : >35}  ∩  {right : <35} {len(intersection)}")
    if args.verbose:
        offset = 35 - len(left)
        for x in intersection:
            print(f"{' ' * offset}\t{x}")

print(f"\nComparing Spotify playlists with local track collection...")
if args.compare_local:
    glob_path = Path('/'.join([args.compare_local, 'DJ Music']))
    tracks = [str(p) for p in glob_path.rglob('**/*.*')]
    tracks_by_folder = {}

    for g, group in groupby(tracks, key=lambda x: os.path.basename(os.path.split(x)[0])):
        tracks_by_folder[g] = set([os.path.basename(x) for x in group])
    
    total = sum([len(x) for x in tracks_by_folder.values()]) * sum([len(x) for x in tracks_by_playlist.values()])
    pbar = tqdm(total=total)
    for a,b in product(tracks_by_folder, tracks_by_playlist):
        files = []
        for x,y in product(tracks_by_folder[a], tracks_by_playlist[b]):
            if fuzz.ratio(x.lower(), y.lower()) >= args.fuzz_ratio:
                files.append((x,y))
            pbar.update(1)

        if files:
            files.sort()
            left = f"[FOLDER] {a.title()} ({len(tracks_by_folder[a])})"
            right = f"[PLAYLIST] {b.title()} ({len(tracks_by_playlist[b])})"
            print(f"{left : >42}  ∩  {right : <45} {len(files)}")
        if args.verbose:
            offset = 42 - len(left)
            for x,y in files:
                print(f"{' ' * offset}\t[{x}]  -->  [{y}]")
    pbar.close()
