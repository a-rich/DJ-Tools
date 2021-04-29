from spotipy.oauth2 import SpotifyClientCredentials
from itertools import combinations, product
from argparse import ArgumentParser
from datetime import datetime
from itertools import groupby
from functools import reduce
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
p.add_argument('--include_dirs', nargs='+',
        help='list of parent folder names to ignore in --path')
p.add_argument('--path', type=str,
        help='path to root of DJ USB')
p.add_argument('--compare_matches', action='store_true',
        help='display matches or misses of fuzzy matching')
p.add_argument('--fuzz_ratio', type=int, default=72,
        help='lower-bound similarity between Spotify and local tracks to consider a match')
p.add_argument('--new', type=parser.parse,
        help='datetime after which songs are considered new')
p.add_argument('--verbose', action='store_true',
        help='verbosity level')
args = p.parse_args()

args.include_dirs = set([x.lower() for x in args.include_dirs]) if args.include_dirs else []


def get_tracks(playlist_id):
    try:
        playlist = spotify.playlist(playlist_id)
    except Exception as e:
        raise Exception(f"failed to get playlist with ID {playlist_id}")
    
    tracks = playlist['tracks']
    result = [f"{x['track']['name']} - {', '.join([y['name'] for y in x['track']['artists']])}"
            for x in tracks['items']]

    while tracks['next']:
        tracks = spotify.next(tracks)
        result.extend([f"{x['track']['name']} - {', '.join([y['name'] for y in x['track']['artists']])}"
                for x in tracks['items']])

    return set(result)


spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
playlists = {k.lower(): v for k,v in json.load(open(args.playlist_data, 'r')).items()}
compare = set([x.lower() for x in args.compare_playlists])
all_ = 'all' in compare 
print(f"Getting track data from Spotify...")
tracks_by_playlist = {k: get_tracks(v) for k,v in playlists.items() if all_ or k in compare}
for k,v in tracks_by_playlist.items():
    print(f"\t{k.title()}: {len(v)}")

if len(tracks_by_playlist) > 1:
    print(f"\nComparing Spotify playlists with each other...")

for a,b in combinations(tracks_by_playlist, 2):
    intersection = set(tracks_by_playlist[a]).intersection(set(tracks_by_playlist[b]))
    if intersection:
        left = f"{a.title()} ({len(tracks_by_playlist[a])})"
        right = f"{b.title()} ({len(tracks_by_playlist[b])})"
        print(f"{left : >35}  ∩  {right : <35} {len(intersection)}")
        offset = 35 - len(left)
        for x in intersection:
            print(f"{' ' * offset}\t{x}")

if args.path:
    print(f"\nComparing Spotify playlists with local track collection...")
    tracks, folders = [], {}
    glob_path = Path('/'.join([args.path, 'DJ Music']))

    for x in [os.path.splitext(str(p))[0] for p in glob_path.rglob('**/*.*')]:
        folder = os.path.basename(os.path.split(x)[0]).lower()
        if args.include_dirs and folder in args.include_dirs:
            tracks.append(x)
            folders[folder] = folders.get(folder, 0) + 1
        if not args.include_dirs:
            folders[folder] = folders.get(folder, 0) + 1

    for k,v in folders.items():
        print(f"\t{k.title()}: {v}")

    tracks_by_folder = {g: set([os.path.basename(x) for x in group])
            for g, group in groupby(tracks, key=lambda x: os.path.basename(os.path.split(x)[0]))}
    all_files = [(x, ' - '.join(x.split(' - ')[-1::-1])) for x in
            set(reduce(lambda a,b: a.union(b), tracks_by_folder.values()))
            if len(x.split(' - ')) > 1]
    all_tracks = set(reduce(lambda a,b: a.union(b), tracks_by_playlist.values()))
    matches, non_matches = set(), dict()
    product = list(product(all_tracks, all_files))

    for x,y in tqdm(product):
        for z in y:
            fuzz_ratio = fuzz.ratio(x.lower(), z.lower())
            if fuzz_ratio >= args.fuzz_ratio:
                matches.add(x)
            else:
                non_matches[x] = max([
                        non_matches.get(x, (-1, None)), 
                        (fuzz_ratio, z)], key=lambda x: x[0])

        if x in matches and x in non_matches:
            del non_matches[x]

    print(f"Matches: {len(list(matches))}\nNon-matches: {len(list(non_matches))}")
    if args.compare_matches:
        for x in sorted(list(matches)):
            print(f"\t{x}")
    else:
        for x,r in non_matches.items():
            print(f"{r[0]}% similarity\n\tSpotify track: [{x}]\n\tLocal track:   [{r[1]}]")
    