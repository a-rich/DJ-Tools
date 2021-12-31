"""This module is responsible for creating or updating Spotify playlists by
querying subreddit top posts. Posts are first checked to see if they are
direct links to a Spotify track. If this is not the case, then the post title
is parsed in an attempt to interpret it as either 'ARTIST NAME - TRACK TITLE'
or 'TRACK TITLE - ARTIST NAME'. These components are then used to search the
Spotify API for tracks. The resulting tracks have their title and artist fields
compared with the reddit post title and are added to the respective playlist
if the Levenshtein similarity passes a threshold.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os
from traceback import format_exc

from fuzzywuzzy import fuzz
import praw
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tqdm import tqdm


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s:%(lineno)s - ' \
                           '%(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('playlist_builder')


def update_auto_playlists(config):
    """This function updates the contents of one or more Spotify playlists with
    the top posts of one or more subreddits (currently only supports one
    subreddit per playlist).

    TODO: implement many-to-many subreddit-playlist multiplicity

    Args:
        config (dict): configuration object
    """
    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=config['SPOTIFY_CLIENT_ID'],
            client_secret=config['SPOTIFY_CLIENT_SECRET'],
            redirect_uri=config['SPOTIFY_REDIRECT_URI'],
            scope='playlist-modify-public'))

    reddit = praw.Reddit(
            client_id=config['REDDIT_CLIENT_ID'],
            client_secret=config['REDDIT_CLIENT_SECRET'],
            user_agent=config['REDDIT_USER_AGENT'])

    ids_path = os.path.join('config', 'playlist_builder.json')
    if os.path.exists(ids_path):
        subreddit_playlist_ids = json.load(open(ids_path, encoding='utf-8'))
    else:
        subreddit_playlist_ids = {}

    for subreddit in config['AUTO_PLAYLIST_SUBREDDITS']:
        playlist_id = subreddit_playlist_ids.get(subreddit)
        if not playlist_id:
            logger.warning(f'Unable to resolve {subreddit} into an ID for ' \
                           'an existing playlist...creating a new playlist')

        new_tracks = get_top_subreddit_posts(spotify, reddit, subreddit,
                                             config)
        if new_tracks:
            if playlist_id:
                playlist = update_existing_playlist(spotify, playlist_id,
                        new_tracks, config['AUTO_PLAYLIST_TRACK_LIMIT'])
            else:
                playlist = build_new_playlist(spotify,
                                              config['SPOTIFY_USERNAME'],
                                              subreddit, new_tracks)
                subreddit_playlist_ids[subreddit] = playlist['id']
                with open(ids_path, 'w', encoding='utf-8') as _file:
                    json.dump(subreddit_playlist_ids, _file)
            logger.info(f"Playlist '{playlist['name']}' URL: " \
                        f"{playlist['external_urls'].get('spotify')}")
        else:
            logger.info('No top tracks for the ' \
                        f"{config['AUTO_PLAYLIST_TOP_PERIOD']} in {subreddit}")


def get_top_subreddit_posts(spotify, reddit, subreddit, config):
    """Filters the top submissions for the provided subreddit' and tries to
    resolve each into a Spotify track until all the submissions are parsed or
    the track limit has been met.

    Args:
        spotify (spotipy.Spotify): spotify client
        reddit (praw.Reddit): reddit client
        subreddit (str): subreddit name to filter
        config (dict): configuration object

    Returns:
        ([(str, str), ...]): list of Spotify track ('id', 'name') tuples
    """
    new_tracks = []
    submissions = list(reddit.subreddit(subreddit).top(limit=None,
            time_filter=config['AUTO_PLAYLIST_TOP_PERIOD']))
    payload = [
            submissions,
            [spotify] * len(submissions),
            [config['AUTO_PLAYLIST_TRACK_LIMIT']] * len(submissions),
            [config['AUTO_PLAYLIST_FUZZ_RATIO']] * len(submissions)
    ]
    with ThreadPoolExecutor(max_workers=8) as executor:
        new_tracks = list(tqdm(executor.map(process, *payload),
                total=len(submissions), desc=f'Filtering r/{subreddit} posts'))
    new_tracks = [track for x in new_tracks for track in x]
    new_tracks = new_tracks[:config['AUTO_PLAYLIST_TRACK_LIMIT']]

    return new_tracks


def process(submission, spotify, limit, threshold):
    """Worker thread process.

    Args:
        submission (praw.Submission): Submission object

    Returns:
        ([TrackObject, ...]): list of one or more TrackObjects
    """
    if 'spotify.com/track/' in submission.url:
        return [(submission.url, submission.title)]
    return fuzzy_match(spotify, submission.title, limit, threshold)


def fuzzy_match(spotify, title, limit, threshold):
    """Attempts to split submission title into two parts
    (track name, artist(s)), search Spotify for tracks that have an
    'artist' field that matches one of these parts and a 'name' field that
    matches the remaining part with a threshold Levenshtein similarity.

    Args:
        spotify (spotipy.Spotify): spotify client
        title (str): submission title
        limit (int): maximum number of Spotify tracks to extract

    Returns:
        ([(str, str), ...]): list of Spotify track ('id', 'name') tuples
    """
    title, artist = parse_title(title)
    if not (title and artist):
        return []

    results = spotify.search(
            q=f"{title.replace(' ', '+')}+{artist.replace(' ', '+')}",
            type='track', limit=limit)

    return [(x['id'], x['name']) for x in filter_results(spotify, results,
                                                         threshold, title,
                                                         artist)]


def parse_title(title):
    """Attempts to split submission title into two parts
    (track name, artist(s)).

    Args:
        title (str): submission title

    Returns:
        (tuple): pair of strings that represent (in no particular order) the
                 artist(s) and track name(s)
    """
    try:
        title, artist = map(str.strip, title.split(' - '))
    except ValueError:
        try:
            title, artist = map(str.strip, title.lower().split(' by '))
        except ValueError:
            return None, None

    title, artist = title.split('(')[0], artist.split('(')[0]
    title, artist = title.split('[')[0], artist.split('[')[0]

    return title, artist


def filter_results(spotify, results, threshold, title, artist):
    """Helper function for applying filtering logic to find tracks that
    match the submission title closely enough.

    Args:
        results ([spotipy.TrackObject, ...]): list of Spotify TrackObjects

    Returns:
        ([spotipy.TrackObject, ...]): list of TrackObjects
    """
    tracks = [filter_tracks(results['tracks']['items'], threshold, title,
                            artist)]
    while results['tracks']['next']:
        try:
            results = spotify.next(results['tracks'])
        except Exception:
            logger.warning(f"Failed to get next tracks: {format_exc()}")
            break
        tracks.append(filter_tracks(results['tracks']['items'], threshold,
                                    title, artist))

    return filter(None, tracks)


def filter_tracks(tracks, threshold, title, artist):
    """Applies Levenshtein distance filtering on both the resulting
    tracks' 'artist' and 'name' fields to qualify a match for the
    submission title.

    Args:
        tracks ([spotipy.TrackObject, ...]): list of Spotify TrackObjects

    Returns:
        (spotify.TrackObject): first TrackObject that matches the submission
                               title
    """
    for track in tracks:
        artists = {x['name'].lower() for x in track['artists']}
        if fuzz.ratio(track['name'].lower(), title.lower()) >= threshold or \
                fuzz.ratio(track['name'].lower(), artist.lower()) >= threshold:
            if any((fuzz.ratio(a, part) >= threshold
                    for part in [title.lower(), artist.lower()]
                    for a in artists)):
                return track


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

    track_count = len(tracks)
    track_index = 0
    ids = {x['track']['id'] for x in tracks}
    remove_payload = []
    add_payload = []
    tracks_added = []

    for id_, track in new_tracks:
        if 'spotify.com/track/' in id_:
            resp = spotify.track(id_)
            id_ = resp['id']
            track = resp['name']
        if id_ in ids:
            continue
        if track_count >= limit:
            track = tracks.pop(0)
            remove_payload.append({"uri": track['track']['uri'],
                                   "positions": [track_index]})
            track_index += 1
        tracks_added.append(track)
        add_payload.append(id_)

    if tracks_added:
        logger.info("Tracks added:")
        for track in tracks_added:
            logger.info(f"\t{track}")

    if remove_payload:
        spotify.playlist_remove_specific_occurrences_of_items(playlist,
                                                              remove_payload)
    if add_payload:
        spotify.playlist_add_items(playlist, add_payload)

    return _playlist


def build_new_playlist(spotify, username, subreddit, new_tracks):
    """Creates a new playlist from a list of track IDs / URLs.

    Args:
        spotify (spotipy.Spotify): spotify client
        subreddit (str): subreddit name to filter
        new_tracks ([(str, str), ...]): list of Spotify track ('id', 'name')
                                        tuples

    Returns:
        (spotipy.Playlist): Playlist object for the newly constructed playlist.
    """
    ids = list(zip(*new_tracks))[0]
    playlist = spotify.user_playlist_create(username,
                                            name=f"r/{subreddit.title()}")
    spotify.playlist_add_items(playlist['id'], ids, position=None)

    return playlist
