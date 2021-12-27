from argparse import ArgumentParser
from datetime import datetime, timezone
from functools import reduce
from itertools import combinations, product, groupby
import json
import os
from pathlib import Path
import sys
from typing import Union

from bs4 import BeautifulSoup
from dateutil.parser import parse
from fuzzywuzzy import fuzz
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tqdm import tqdm



def get_playlist_label(_spotify, q): 
    """Get artists from URL, file, or CLI arg and fetches all albums by artists
       from Spotify. If album has a label ~= --label, then those tracks are
       added to a new playlist with the same name as --label.
    Args:
        _spotify (spotipy.Spotify): spotify object
        q (str): either URL to Beatport record label page, URL to Bandcamp
                artist page, path to file with artists separated by newline,
                or space-delimited list of artists
    """

    def get_artist_tracks(q): 
        """Search Spotify for artist name, filter for names matching closely
           enough, and get their tracks which belong to --label.
        Args:
            q (str): name of an artist
        Returns:
            data (dict): mapping album ID to list of tracks
        """

        def filter_artists(_artists):
            """If Spotify artist name fuzzy matches _artist closely enough, get
               their albums.
            Args:
                _artists (str): name of an artist
            Returns:
                artist_album_tracks (dict): mapping album ID to list of tracks
            """

            def get_artist_albums(_artist):
                """Gets the albums of _artist and filters for label fuzzy
                   matching --label closely enough.
                Args:
                    _artists (str): name of an artist
                Returns:
                    albums (list): list of tracks
                """

                def filter_albums(_albums):
                    """Gets the albums of _artist and filters for label fuzzy
                    matching --label closely enough.
                    Args:
                        _albums (list): Spotify album objects
                    Returns:
                        album_matches (list): list of track (id, name)
                    """
                    album_matches = []
                    for x in _albums:
                        x = _spotify.album(x['id'])
                        fuzz_ratio = fuzz.ratio(x['label'].lower(), args.label)
                        if fuzz_ratio > args.fuzz_ratio:
                            album_matches.append([x['id'], x['name']])
                    
                    return album_matches

                albums_ = _spotify.artist_albums(_artist)
                albums = filter_albums(albums_['items'])
                while albums_['next']:
                    albums_ = _spotify.next(albums_)
                    albums.extend(filter_albums(albums_['items']))

                return albums

            artist_album_tracks = {}
            for x in _artists:
                fuzz_ratio = fuzz.ratio(x['name'].lower(), q.lower())
                if fuzz_ratio > args.get_artists_fuzz_ratio:
                    albums = get_artist_albums(x['id'])
                    if albums:
                        artist_album_tracks[x['id']] = {'name': x['name'], 'albums': []}
                        print(f"\t{fuzz_ratio}% match: {x['name']}, {x['id']}, {len(albums)} matching albums")
                    for album, name in albums:
                        if name in seen:
                            continue
                        album_tracks_ = _spotify.album_tracks(album)
                        album_tracks = album_tracks_['items']
                        while album_tracks_['next']:
                            album_tracks_ = _spotify.next(album_tracks_)
                            album_tracks.extend(album_tracks_['items'])
                        artist_album_tracks[x['id']]['albums'].append({'id': album, 'name': name, 'tracks': album_tracks})

            return artist_album_tracks

        artists_ = spotify.search(q='artist:' + q, type='artist') 
        data = filter_artists(artists_['artists']['items'])
        while artists_['artists']['next']: 
            try:
                artists_ = spotify.next(artists_['artists']) 
                data.update(filter_artists(artists_['artists']['items'])) 
            except Exception as e:
                print(f"Exception while getting artists...")
                break
        
        return data 
        
    # Get list of artists belonging to --label
    soup = BeautifulSoup(requests.get(q).text, 'html.parser')
    if 'beatport' in q:
        artist_tab = soup.find_all("div", {"class":"filter-drop filter-artists-drop"})[0]
        artists = [x.text[:-2] for x in artist_tab.find_all("label", {"class":"filter-drop-checkbox-label"})]
    elif 'http' in q:
        artists = [x.text for x in soup.find_all("div", {"class":"artists-grid-name"})]
    else:
        if os.path.exists(q):
            artists = [x.strip() for x in open(q, 'r').readlines()]
        elif len(q.split(' ')):
            artists = a.split(' ')
    artists = set(artists)
    data = {}
    seen = set()
    tracks = set()

    # Get the tracks of artists' albums belonging to --label
    print(f"Getting tracks for record label {args.label.title()}...")
    for a in tqdm(artists, desc="Getting artists' tracks"):
        data.update(get_artist_tracks(a))
    
    if data:
        playlist = spotify.user_playlist_create(args.spotify_user_name, name=args.label.title())  

    # Ensure uniqueness of tracks / albums before adding to a new Spotify playlist
    print(f"Adding tracks to {playlist['name']}...")
    albums = sorted([x for v in data.values() for x in v['albums'] if x['tracks']], key=lambda x : x['name'])
    for album in albums:
        if album['name'] in seen:
            continue
        seen.add(album['name'])
        _new_tracks = []
        for x in album['tracks']:
            if x['name'] not in tracks:
                tracks.add(x['name'])
                _new_tracks.append(x['id'])

        print(f"\t{album['name']}: {len(_new_tracks)}")
        if _new_tracks:
            spotify.playlist_add_items(playlist['id'], _new_tracks, position=None)

    print(f"Playlist '{playlist['name']}' URL: {playlist['external_urls'].get('spotify')}")


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
    for p in glob_path.rglob('**/[!.]*.*'):
        x = os.path.splitext(str(p))[0]
        _ = [p.stat().st_mtime, x]
        _most_recent = max([_most_recent, _], key=lambda y: y[0])
        folder = os.path.basename(os.path.split(x)[0]).lower()
        if (args.include_dirs and folder in args.include_dirs) or not args.include_dirs:
            tracks.append(x)
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
    
    if args.find_new and args.date:
        _most_recent = [args.date, '']

    return _tracks_by_folder, _most_recent


def find_new_tracks(_tracks_by_playlist, _most_recent):
    """Display playlist tracks added after the most recently added local track.
    Args:
        _tracks_by_playlist (dict): playlist name mapped to set of (track name, date added)
        _most_recent (list): datetime and track name for most recently added track
    Returns:
        (list): list of tracks that might be new
    """
    print("Finding newer tracks in each playlist...")
    _new_tracks = []
    for k,v in _tracks_by_playlist.items():
        v = list(filter(lambda x: x[1] > _most_recent[0], sorted(v, key=lambda x: x[1], reverse=True)))
        if v:
            print(k.title())
        for track, date in v:
            print(f"\t{date}: {track}")
            _new_tracks.append(track)

    return _new_tracks


def compare_local_tracks(_tracks_by_playlist, _tracks_by_folder, _new_tracks):
    """Display tracks across all Spotify playlists that do not match
       (within --fuzz_ratio) any local tracks.
    Args:
        _tracks_by_playlist (dict): playlist name mapped to set of (track name, date added)
        _tracks_by_folder (dict): folder name mapped to set of track names
    """
    print(f"\nComparing Spotify playlists with local track collection...")
    _all_files = [(x, ' - '.join(x.split(' - ')[-1::-1])) for x in
            set(reduce(lambda a,b: a.union(b), _tracks_by_folder.values()))
            if len(x.split(' - ')) > 1]

    if type(_new_tracks) is list:
        _all_tracks = set(_new_tracks)
    else:
        _all_tracks = set()
        for playlist, tracks in _tracks_by_playlist.items():
            _all_tracks.update(list(zip(*tracks))[0])

        # why no workie?!
        # _all_tracks = set(reduce(lambda a,b: set(list(zip(*a))[0]).union(b), _tracks_by_playlist.values()))

    matches, non_matches = dict(), dict()
    for x,y in tqdm(list(product(_all_tracks, _all_files))):
        for z in y:
            fuzz_ratio = fuzz.ratio(x.lower(), z.lower())
            if fuzz_ratio >= args.fuzz_ratio:
                matches[x] = max([
                        matches.get(x, (-1, None)), 
                        (fuzz_ratio, z)], key=lambda x: x[0])
            else:
                non_matches[x] = max([
                        non_matches.get(x, (-1, None)), 
                        (fuzz_ratio, z)], key=lambda x: x[0])

        if x in matches and x in non_matches:
            del non_matches[x]

    if args.compare_matches or _new_tracks:
        print(f"Matches: {len(list(matches))}")
        for x,r in matches.items():
            print(f"\t{r[0]}% similarity\n\tSpotify track: [{x}]\n\tLocal track:   [{r[1]}]")
        print(f"Non-matches: {len(list(non_matches))}")
    else:
        print(f"Non-matches: {len(list(non_matches))}")
        for x,r in non_matches.items():
            print(f"\t{r[0]}% similarity\n\tSpotify track: [{x}]\n\tLocal track:   [{r[1]}]")
        print(f"Matches: {len(list(matches))}")




if __name__ == '__main__':
    def date_checker(x):
        try:
            return parse(x)
        except Exception:
            return None

    p = ArgumentParser()
    p.add_argument('--get_tracks_by_label', type=str,
            help="given a record label's artists page URL (only Beatport and Bandcamp are supported), find all Spotify tracks")
    p.add_argument('--label', type=str,
            help='name of record label')
    p.add_argument('--spotify_user_name', type=str, default='alex.richards006',
            help='Spotify user to create new playlists under')
    p.add_argument('--playlist_data', type=str, default='playlist_data.json',
            help='path to playlist JSON; mapping of playlist_name to playlist_id')
    p.add_argument('--playlists', nargs='+',
            help='list of Spotify Playlist names to compare for track overlap')
    p.add_argument('--compare_playlists', action='store_true',
            help='find overlap between Spotify playlists')
    subparsers = p.add_subparsers(dest='find_new', help='find_new option subparser')
    find_new_subparser = subparsers.add_parser(name='find_new',
            help="provide `find_new` alone to use local track's date modified field; otherwise provide `--date` datetime string")
    find_new_subparser.add_argument('--date', type=date_checker)
    p.add_argument('--compare_local', action='store_true',
            help='find overlaping (or missing) files between Spotify and local')
    p.add_argument('--path', type=str,
            help='path to root of DJ USB')
    p.add_argument('--include_dirs', nargs='+',
            help='list of parent folder names to search in --path')
    p.add_argument('--compare_matches', action='store_true',
            help='display matches or misses of fuzzy matching')
    p.add_argument('--fuzz_ratio', type=int, default=72,
            help='lower-bound similarity between Spotify and local tracks to consider a match')
    p.add_argument('--get_artists_fuzz_ratio', type=int, default=95,
            help='lower-bound similarity between artist names when finding tracks by label')
    p.add_argument('--verbose', action='store_true',
            help='verbosity level')
    args = p.parse_args()
    args.include_dirs = set([x.lower() for x in args.include_dirs]) if args.include_dirs else []

    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(scope='playlist-modify-public'))

    if args.get_tracks_by_label:
        if not args.label:
            sys.exit('must provide label name if get tracks by label')
        get_playlist_label(spotify, args.get_tracks_by_label)
        sys.exit()

    tracks_by_playlist = get_tracks_spotify(spotify)

    if args.compare_playlists and len(tracks_by_playlist) > 1:
        compare_playlists(tracks_by_playlist)

    if args.find_new or args.compare_local:
        if not args.path or not os.path.exists(args.path):
            sys.exit("you must provide the --path to the root of your DJ USB in order to find the newest playlist tracks or compare playlists tracks with local tracks")
        tracks_by_folder, most_recent = get_tracks_local()

    new_tracks = None
    if args.find_new:
        new_tracks = find_new_tracks(tracks_by_playlist, most_recent)

    if args.compare_local:
        try:
            import Levenshtein
        except:
            print(f"[WARNING]: you can get a huge speed boost fuzzy matching local files if you run `pip install python-Levenshtein`")

        compare_local_tracks(tracks_by_playlist, tracks_by_folder, new_tracks)
