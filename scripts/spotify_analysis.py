from spotipy.oauth2 import SpotifyClientCredentials
from itertools import combinations, product
from datetime import datetime, timezone
from argparse import ArgumentParser
from itertools import groupby
from functools import reduce
from fuzzywuzzy import fuzz
from pathlib import Path
from tqdm import tqdm
import spotipy
import json
import os



def get_tracks_spotify(_spotify):
    """Get tracks from all Spotify playlists in --playlist_data or the subset
       that is --playlists.
    Args:
        _spotify (spotipy.Spotify): spotify object
    Returns:
        dict: playlist name mapped to set of track names
    """

    def get_tracks(playlist_id):
        """Get tracks from a playlist.
        Args:
            playlist_id (string): playlist ID to get tracks with
        Raises:
            Exception: failure to get playlist
        Returns:
            set: (track name, date added)
        """
        try:
            playlist = _spotify.playlist(playlist_id)
        except Exception:
            raise Exception(f"failed to get playlist with ID {playlist_id}")
        
        tracks = playlist['tracks']


        result = [(f"{x['track']['name']} - {', '.join([y['name'] for y in x['track']['artists']])}",
                datetime.fromtimestamp(datetime.strptime(x['added_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()))
                for x in tracks['items']]

        while tracks['next']:
            tracks = _spotify.next(tracks)
            result.extend([(f"{x['track']['name']} - {', '.join([y['name'] for y in x['track']['artists']])}",
                datetime.fromtimestamp(datetime.strptime(x['added_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()))
                for x in tracks['items']])

        return set(result)

    playlists = {k.lower(): v for k,v in json.load(open(args.playlist_data, 'r')).items()}
    compare = set([x.lower() for x in args.playlists]) if args.playlists else set()
    _tracks_by_playlist = {k: get_tracks(v) 
            for k,v in tqdm({k:v for k,v in playlists.items()
                            if not compare or k in compare}.items(),
                    desc='Query Spotify Tracks')}

    if args.verbose:
        for k,v in _tracks_by_playlist.items():
            print(f"\t{k.title()}: {len(v)}")
        print()

    return _tracks_by_playlist


def compare_playlists(_tracks_by_playlist):
    """Prints the intersection between all combinations of playlists.
    Args:
        _tracks_by_playlist (dict): playlist name mapped to set of (track name, date added)
    """
    print(f"Comparing Spotify playlists for overlapping tracks...")
    for a,b in combinations(_tracks_by_playlist, 2):
        intersection = set(x[0] for x in _tracks_by_playlist[a]).intersection(set(x[0] for x in _tracks_by_playlist[b]))
        if intersection:
            left = f"{a.title()} ({len(_tracks_by_playlist[a])})"
            right = f"{b.title()} ({len(_tracks_by_playlist[b])})"
            print(f"{left : >35}  ∩  {right : <35} {len(intersection)}")
            offset = 35 - len(left)
            for x in intersection:
                print(f"{' ' * offset}\t{x}")
    print()


def get_tracks_local():
    """Glob all files in --path (make sure it's only music!)
    Returns:
        (dict, tuple): tracks_by_folder, most recent track (name, date)
    """
    tracks, folders = [], {}
    glob_path = Path('/'.join([args.path, 'DJ Music']))
    _most_recent = [0, None]

    print(f"Globbing local tracks...")
    for p in glob_path.rglob('**/*.*'):
        x = os.path.splitext(str(p))[0]
        _most_recent = [max(_most_recent[0], p.stat().st_mtime), x]
        folder = os.path.basename(os.path.split(x)[0]).lower()
        if args.include_dirs and folder in args.include_dirs:
            tracks.append(x)
            folders[folder] = folders.get(folder, 0) + 1
        if not args.include_dirs:
            folders[folder] = folders.get(folder, 0) + 1
    _most_recent[0] = datetime.fromtimestamp(_most_recent[0])

    if args.verbose:
        for k,v in folders.items():
            print(f"\t{k.title()}: {v}")
        print()

        newest_date, newest_track = _most_recent
        print(f"Newest track is [{os.path.basename(os.path.split(newest_track)[0])}] {os.path.basename(newest_track)}: {newest_date}")
        
    _tracks_by_folder = {g: set([os.path.basename(x) for x in group])
            for g, group in groupby(tracks, key=lambda x: os.path.basename(os.path.split(x)[0]))}

    return _tracks_by_folder, _most_recent


def find_new_tracks(_tracks_by_playlist, _most_recent):
    """Display playlist tracks added after the most recently added local track.
    Args:
        _tracks_by_playlist (dict): playlist name mapped to set of (track name, date added)
        _most_recent (list): datetime and track name for most recently added track
    """
    print("Finding newer tracks in each playlist...")
    for k,v in _tracks_by_playlist.items():
        v = list(filter(lambda x: x[1] > _most_recent[0], sorted(v, key=lambda x: x[1], reverse=True)))
        if v:
            print(k.title())
        for track, date in v:
            print(f"\t{date}: {track}")


def compare_local_tracks(_tracks_by_playlist, _tracks_by_folder):
    """Display tracks across all Spotify playlists that do not match
       (within --fuzz_ratio) any local tracks.
    Args:
        _tracks_by_playlist (dict): playlist name mapped to set of (track name, date added)
        _tracks_by_folder (dict): folder name mapped to set of track names
    """
    _all_files = [(x, ' - '.join(x.split(' - ')[-1::-1])) for x in
            set(reduce(lambda a,b: a.union(b), _tracks_by_folder.values()))
            if len(x.split(' - ')) > 1]

    _all_tracks = set()
    for playlist, tracks in _tracks_by_playlist.items():
        _all_tracks.update(list(zip(*tracks))[0])

    # why no workie?!
    # _all_tracks = set(reduce(lambda a,b: set(list(zip(*a))[0]).union(b), _tracks_by_playlist.values()))

    matches, non_matches = set(), dict()
    for x,y in tqdm(list(product(_all_tracks, _all_files))):
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




if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('--playlist_data', type=str, default='playlist_data.json',
            help='path to playlist JSON; mapping of playlist_name to playlist_id')
    p.add_argument('--playlists', nargs='+',
            help='list of Spotify Playlist names to compare for track overlap')
    p.add_argument('--compare_playlists', action='store_true',
            help='find overlap between Spotify playlists')
    p.add_argument('--find_new', action='store_true',
            help='find new tracks in provided Spotify playlists')
    p.add_argument('--compare_local', action='store_true',
            help='find overlaping (or missing) files between Spotify and local')
    p.add_argument('--path', type=str,
            help='path to root of DJ USB')
    p.add_argument('--include_dirs', nargs='+',
            help='list of parent folder names to ignore in --path')
    p.add_argument('--compare_matches', action='store_true',
            help='display matches or misses of fuzzy matching')
    p.add_argument('--fuzz_ratio', type=int, default=72,
            help='lower-bound similarity between Spotify and local tracks to consider a match')
    p.add_argument('--verbose', action='store_true',
            help='verbosity level')
    args = p.parse_args()
    args.include_dirs = set([x.lower() for x in args.include_dirs]) if args.include_dirs else []

    spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    tracks_by_playlist = get_tracks_spotify(spotify)

    if args.compare_playlists and len(tracks_by_playlist) > 1:
        compare_playlists(tracks_by_playlist)

    if args.find_new or args.compare_local:
        tracks_by_folder, most_recent = get_tracks_local()

    if args.find_new:
        find_new_tracks(tracks_by_playlist, most_recent)

    if args.compare_local:
        try:
            import Levenshtein
        except:
            print(f"[WARNING]: you can get a huge speed boost fuzzy matching local files if you run `pip install python-Levenshtein`")

        print(f"\nComparing Spotify playlists with local track collection...")
        compare_local_tracks(tracks_by_playlist, tracks_by_folder)


