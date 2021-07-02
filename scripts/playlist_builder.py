from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
import json
import os
import sys
import time

from dateutil import parser
from fuzzywuzzy import fuzz
import praw
import psutil
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tqdm import tqdm



def get_top_subreddit_posts(spotify, subreddit, limit):
    """Filters the top '--time_filter' (default is 'week') submissions for the
    provided '--subreddit' and tries to resolve each into a Spotify track until
    all the submissions are parsed or '--limit' has been met.

    Args:
        spotify (spotipy.Spotify): spotify client
        subreddit (str): subreddit name to filter
        limit (int): maximum number of Spotify tracks to extract
    
    Returns:
        ([(str, str), ...]): list of Spotify track ('id', 'name') tuples
    """
    def fuzzy_match(spotify, title, limit):
        """Attempts to split submission title into two parts
        (track name, artist(s)), search Spotify for tracks that have an
        'artist' field that matches one of these parts and a 'name' field that
        matches the remaining part with a Levenshtein similarity no less than
        '--fuzz_ratio'.

        Args:
            spotify (spotipy.Spotify): spotify client
            title (str): submission title
            limit (int): maximum number of Spotify tracks to extract
        
        Returns:
            ([(str, str), ...]): list of Spotify track ('id', 'name') tuples
        """
        def filter_results(results):
            """Helper function for applying filtering logic to find tracks that
            match the submission title closely enough.

            Args:
                results ([spotipy.TrackObject, ...]): list of Spotify TrackObjects

            Returns:
                ([spotipy.TrackObject, ...]): list of TrackObjects
            """
            tracks = [filter_tracks(results['tracks']['items'])]
            while results['tracks']['next']:
                results = spotify.next(results['tracks'])
                tracks.append(filter_tracks(results['tracks']['items']))

            return filter(None, tracks)
            
        def filter_tracks(tracks):
            """Applies Levenshtein distance filtering on both the resulting
            tracks' 'artist' and 'name' fields to qualify a match for the
            submission title.

            Args:
                tracks ([spotipy.TrackObject, ...]): list of Spotify TrackObjects

            Returns:
                (spotify.TrackObject): first TrackObject that matches the submission title
            """
            for t in tracks:
                artists = set([x['name'].lower() for x in t['artists']])
                if fuzz.ratio(t['name'].lower(), x.lower()) >= args.fuzz_ratio \
                        or fuzz.ratio(t['name'].lower(), y.lower()) >= args.fuzz_ratio:
                    if any([fuzz.ratio(a, z) >= args.fuzz_ratio for z in [x.lower(), y.lower()] for a in artists]):
                        return t
        
        def parse_title(title):
            """Attempts to split submission title into two parts
            (track name, artist(s)).

            Args:
                title (str): submission title

            Returns:
                (tuple): pair of strings that represent (in no particular order) the artist(s) and track name(s)
            """
            try:
                x, y = map(str.strip, title.split(' - '))
            except ValueError:
                try:
                    x, y = map(str.strip, title.lower().split(' by '))
                except ValueError:
                    return None, None

            x, y = x.split('(')[0], y.split('(')[0]
            x, y = x.split('[')[0], y.split('[')[0]
        
            return x, y

        x, y = parse_title(title)
        if not (x or y):
            return []

        results = spotify.search(q=f"{x.replace(' ', '+')}+{y.replace(' ', '+')}", type='track', limit=limit)

        return [(x['id'], x['name']) for x in filter_results(results)]
    
    def process(submission):
        """Worker thread process.

        Args:
            submission (praw.Submission): Submission object

        Returns:
            ([TrackObject, ...]): list of one or more TrackObjects
        """
        if 'spotify.com/track/' in submission.url:
            return [(submission.url, submission.title)]
        else:
            return fuzzy_match(spotify, submission.title, limit)

    reddit = praw.Reddit(
        client_id=os.environ.get('REDDIT_CLIENT_ID'),
        client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
        user_agent='Playlist Builder')

    new_tracks = []
    submissions = list(reddit.subreddit(subreddit).top(limit=None,
            time_filter=args.time_filter))
    with ThreadPoolExecutor(max_workers=psutil.cpu_count()*2) as executor:
        new_tracks = list(tqdm(executor.map(process, submissions),
                total=len(submissions), desc=f'Filtering r/{subreddit} posts'))
    new_tracks = [track for x in new_tracks for track in x]
    new_tracks = new_tracks[:limit]

    return new_tracks 


def build_new_playlist(spotify, subreddit, new_tracks):
    """Creates a new playlist from a list of track IDs / URLs.

    Args:
        spotify (spotipy.Spotify): spotify client
        subreddit (str): subreddit name to filter
        new_tracks ([(str, str), ...]): list of Spotify track ('id', 'name') tuples
    
    Returns:
        (spotipy.Playlist): Playlist object for the newly constructed playlist.
    """
    ids = list(zip(*new_tracks))[0]
    playlist = spotify.user_playlist_create(args.spotify_user_name, name=f"r/{subreddit.title()}")  
    spotify.playlist_add_items(playlist['id'], ids, position=None)

    return playlist


def update_existing_playlist(spotify, playlist, new_tracks, limit):
    """Adds new tracks to an existing playlist; removes old tracks if the 

    Args:
        spotify ([type]): [description]
        playlist ([type]): [description]
        new_tracks ([type]): [description]

    Returns:
        (spotipy.Playlist): Playlist object for the newly constructed playlist.
    """
    _playlist = spotify.playlist(playlist)
    tracks = _playlist['tracks']['items']
    while _playlist['tracks']['next']:
        _playlist = spotify.next(_playlist['tracks'])
        tracks.extend(_playlist['tracks']['items'])
    
    tracks = sorted(tracks, key=lambda x: parser.parse(x['added_at']), reverse=True)
    ids = set([x['track']['id'] for x in tracks])

    present, absent = [], []
    for id_, track in new_tracks:
        if 'spotify.com/track/' in id_:
            resp = spotify.track(id_)
            id_ = resp['id']
            track = resp['name']
        if id_ in ids:
            present.append(track)
            continue
        if len(tracks) >= limit:
            spotify.playlist_remove_specific_occurrences_of_items(playlist, [ids.pop()])
        absent.append(track)
        spotify.playlist_add_items(playlist, [id_])
    
    if present:
        print(f"Tracks already present in the playlist:")
        for x in sorted(present):
            print(f"\t{x}")
        print()

    if absent:
        print(f"Tracks added:")
        for x in sorted(absent):
            print(f"\t{x}")
        print()
    
    return _playlist


if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('--subreddit', type=str,
            required=True, help='subreddit to create Spotify playlist from')
    p.add_argument('--limit', type=int, default=50,
            help='number of top tracks to put in the playlist')
    p.add_argument('--time_filter', type=str, default='week',
            choices=['all', 'day', 'hour', 'month', 'week', 'year'],
            help='time period to search top for')
    p.add_argument('--fuzz_ratio', type=int, default=50,
            help='minimium Levenshtein distance between post title componenet and spotify artist search result')
    p.add_argument('--spotify_user_name', type=str, default='alex.richards006',
            help='Spotify user to create new playlists under')
    args = p.parse_args()

    if os.path.exists('subreddit_playlist-ids.json'):
        subreddit_playlist_ids = json.load(open('subreddit_playlist-ids.json', 'r'))
    else:
        subreddit_playlist_ids = {}

    playlist_id = subreddit_playlist_ids.get(args.subreddit)
    if not playlist_id:
        print(f'Unable to resolve {args.subreddit} into an ID for an existing playlist...creating a new playlist')

    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(scope='playlist-modify-public'))
    new_tracks = get_top_subreddit_posts(spotify, args.subreddit, args.limit)

    if playlist_id:
        playlist = update_existing_playlist(spotify, playlist_id, new_tracks, args.limit)
    else:
        playlist = build_new_playlist(spotify, args.subreddit, new_tracks)
        subreddit_playlist_ids[args.subreddit] = playlist['id']
        json.dump(subreddit_playlist_ids, open('subreddit_playlist-ids.json', 'w'))

    print(f"Playlist '{playlist['name']}' URL: {playlist['external_urls'].get('spotify')}")