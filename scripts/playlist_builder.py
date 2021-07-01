from argparse import ArgumentParser
import os
import sys

from dateutil import parser
from fuzzywuzzy import fuzz
import praw
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tqdm import tqdm


def get_top_subreddit_posts(spotify, subreddit, limit=50):

    def fuzzy_match(spotify, title):

        def filter_results(results):
            tracks = [filter_tracks(results['tracks']['items'])]
            while results['tracks']['next']:
                results = spotify.next(results['tracks'])
                tracks.append(filter_tracks(results['tracks']['items']))

            return filter(None, tracks)
            
        def filter_tracks(tracks):
            for t in tracks:
                artists = set([x['name'].lower() for x in t['artists']])
                if fuzz.ratio(t['name'].lower(), x.lower()) >= args.fuzz_ratio \
                        or fuzz.ratio(t['name'].lower(), y.lower()) >= args.fuzz_ratio:
                    if any([fuzz.ratio(a, z) >= args.fuzz_ratio for z in [x.lower(), y.lower()] for a in artists]):
                        return t
        
        def parse_title(title):
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

        results = spotify.search(q=f"{x.replace(' ', '+')}+{y.replace(' ', '+')}", type='track', limit=50)

        return [x['id'] for x in filter_results(results)]

    reddit = praw.Reddit(
        client_id=os.environ.get('REDDIT_CLIENT_ID'),
        client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
        user_agent='Playlist Builder')
    urls = []

    with tqdm(total=args.limit) as pbar:
        for submission in reddit.subreddit(subreddit).top(limit=None, time_filter=args.time_filter):
            if 'spotify.com/track/' in submission.url:
                urls.append(submission.url)
                pbar.update(1)
            else:
                x = fuzzy_match(spotify, submission.title)
                if x:
                    urls.extend(x)
                    pbar.update(1)

            if len(urls) == 50:
                break

    return urls


def build_new_playlist(spotify, subreddit, new_tracks):
    playlist = spotify.user_playlist_create(args.spotify_user_name, name=subreddit.title())  
    spotify.playlist_add_items(playlist['id'], new_tracks, position=None)
    print(f"Playlist '{playlist['name']}' URL: {playlist['external_urls'].get('spotify')}")


def update_existing_playlist(spotify, playlist, new_tracks):
    _playlist = spotify.playlist(playlist)
    tracks = _playlist['tracks']['items']
    while _playlist['tracks']['next']:
        _playlist = spotify.next(_playlist['tracks'])
        tracks.extend(_playlist['tracks']['items'])
    
    tracks = sorted(tracks, key=lambda x: parser.parse(x['added_at']), reverse=True)
    ids = set([x['track']['id'] for x in tracks])

    for track in new_tracks:
        if track in ids:
            print(f"track {track} is already there")
            continue
        if len(tracks) == 50:
            removed = ids.pop()
            print(f"playlist is full; {removed} removed and {track} added")
            spotify.playlist_remove_specific_occurrences_of_items(args.playlist, [removed])
            spotify.playlist_add_items(args.playlist, [track])


if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('--subreddit', type=str, default='futurebeats',
            required=True, help='subreddit to create Spotify playlist from')
    p.add_argument('--playlist', type=str, default='7hkMIW8SvbECODRyE9d8Ct',
            choices='7hkMIW8SvbECODRyE9d8Ct', help='playlist ID to update')
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

    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(scope='playlist-modify-public'))
    new_tracks = get_top_subreddit_posts(spotify, args.subreddit, args.limit)

    if not args.playlist:
        build_new_playlist(spotify, args.subreddit, new_tracks)
    else:
        update_existing_playlist(spotify, args.playlist, new_tracks)