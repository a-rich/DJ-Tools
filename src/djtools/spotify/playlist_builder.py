"""This module is responsible for creating or updating Spotify playlists by
querying subreddit posts. Posts are first checked to see if they are direct
links to a Spotify track. If this is not the case, then the post title is
parsed in an attempt to interpret it as either 'ARTIST NAME - TRACK TITLE' or
'TRACK TITLE - ARTIST NAME'. These components are then used to search the
Spotify API for tracks. The resulting tracks have their title and artist fields
compared with the reddit post title and are added to the respective playlist
if the Levenshtein similarity passes a threshold.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import logging
from operator import itemgetter
import os
from traceback import format_exc

from fuzzywuzzy import fuzz
import praw
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tqdm import tqdm

# silence PRAW, Spotify, and urllib3 loggers
for logger in ['prawcore', 'spotipy', 'urllib3']:
    logger = logging.getLogger(logger)
    logger.setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)


def update_auto_playlists(config):
    """This function updates the contents of one or more Spotify playlists with
    the posts of one or more subreddits (currently only supports one subreddit
    per playlist).

    TODO: implement many-to-many subreddit-playlist multiplicity

    Args:
        config (dict): configuration object
    
    Raises:
        KeyError: 'SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET', and
                  'SPOTIFY_REDIRECT_URI' must be configured
        KeyError: 'REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', and
                  'REDDIT_USER_AGENT' must be configured
        KeyError: 'SPOTIFY_USERNAME' must be configured
    """
    try:
        spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=config['SPOTIFY_CLIENT_ID'],
                client_secret=config['SPOTIFY_CLIENT_SECRET'],
                redirect_uri=config['SPOTIFY_REDIRECT_URI'],
                scope='playlist-modify-public',
                requests_timeout=10,
                cache_path=os.path.join(os.path.dirname(__file__),
                                        '.cache').replace(os.sep, '/')))
    except KeyError:
        raise KeyError('Using the playlist_builder module requires the ' \
                       'following config options: SPOTIFY_CLIENT_ID, ' \
                       'SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI') \
                from KeyError 

    try:
        reddit = praw.Reddit(
                client_id=config['REDDIT_CLIENT_ID'],
                client_secret=config['REDDIT_CLIENT_SECRET'],
                user_agent=config['REDDIT_USER_AGENT'])
    except KeyError:
        raise KeyError('Using the playlist_builder module requires the ' \
                       'following config options: REDDIT_CLIENT_ID, ' \
                       'REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT') from KeyError

    ids_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
            'configs', 'playlist_builder.json').replace(os.sep, '/')
    if os.path.exists(ids_path):
        with open(ids_path, encoding='utf-8') as _file:
            subreddit_playlist_ids = json.load(_file)
    else:
        subreddit_playlist_ids = {}
    
    if not config.get('AUTO_PLAYLIST_SUBREDDITS'):
        logger.warn('Using the playlist_builder module requires the config ' \
                    'option AUTO_PLAYLIST_SUBREDDITS')
        return

    for subreddit in config['AUTO_PLAYLIST_SUBREDDITS']:
        playlist_id = subreddit_playlist_ids.get(subreddit['name'])
        if not playlist_id:
            try:
                username = config['SPOTIFY_USERNAME']
            except KeyError:
                raise KeyError('Building a new playlist in the ' \
                               'playlist_builder module requires the config ' \
                               'option SPOTIFY_USERNAME') from KeyError
        tracks = get_subreddit_posts(spotify, reddit, subreddit, config)
        logger.info(f'Got {len(tracks)} track(s) from "r/{subreddit["name"]}"')
        if playlist_id:
            playlist = update_existing_playlist(spotify, playlist_id, tracks,
                                                subreddit['limit'],
                                                config.get('VERBOSITY', 0))
        else:
            logger.warning(f'Unable to get ID for {subreddit["name"]}...' \
                            'creating a new playlist')
            playlist = build_new_playlist(spotify, username, subreddit['name'],
                                          tracks)
            subreddit_playlist_ids[subreddit['name']] = playlist['id']
            with open(ids_path, 'w', encoding='utf-8') as _file:
                json.dump(subreddit_playlist_ids, _file, indent=2)
        logger.info(f"'{playlist['name']}': " \
                    f"{playlist['external_urls'].get('spotify')}")


def get_subreddit_posts(spotify, reddit, subreddit, config):
    """Filters the submissions for the provided subreddit' and tries to resolve
    each into a Spotify track until all the submissions are parsed or the track
    limit has been met.

    Args:
        spotify (spotipy.Spotify): spotify client
        reddit (praw.Reddit): reddit client
        subreddit (dict): 'name', 'type', 'period', and 'limit'
        config (dict): configuration object

    Returns:
        ([(str, str), ...]): list of Spotify track ('id', 'name') tuples
    """
    sub = reddit.subreddit(subreddit['name'])
    sub_funcs = {'top': sub.top,
                 'hot': sub.hot,
                 'new': sub.new,
                 'rising': sub.rising,
                 'controversial': sub.controversial}
    subreddit_limit = config.get('AUTO_PLAYLIST_SUBREDDIT_LIMIT', 500) or None
    try:
        submissions = list(sub_funcs[subreddit['type']](limit=subreddit_limit,
                time_filter=subreddit['period']))
        logger.info(f'"r/{subreddit["name"]}" has {len(submissions)} ' \
                    f"{subreddit['type']} posts for the {subreddit['period']}")
    except TypeError:
        submissions = list(sub_funcs[subreddit['type']](limit=subreddit_limit))
        logger.info(f'"r/{subreddit["name"]}" has {len(submissions)} ' \
                    f"{subreddit['type']} posts")

    new_tracks = []
    payload = [submissions,
              [spotify] * len(submissions),
              [config.get('AUTO_PLAYLIST_FUZZ_RATIO', 50)] * len(submissions)]
    with ThreadPoolExecutor(max_workers=8) as executor:
        new_tracks = list(tqdm(executor.map(process, *payload),
                total=len(submissions), desc=f'Filtering r/{subreddit} posts'))
    new_tracks = [track for track in new_tracks if track]
    new_tracks = new_tracks[:subreddit['limit']]

    return new_tracks


def process(submission, spotify, threshold):
    """Worker thread process.

    Args:
        submission (praw.Submission): Submission object
        spotify (spotipy.Spotify): Spotify API client
        threshold (float): minimum Levenshtein distance

    Returns:
        ([TrackObject, ...]): list of one or more TrackObjects
    """
    if 'spotify.com/track/' in submission.url:
        return (submission.url, submission.title)
    return fuzzy_match(spotify, submission.title, threshold)


def fuzzy_match(spotify, title, threshold):
    """Attempts to split submission title into two parts
    (track name, artist(s)), search Spotify for tracks that have an
    'artist' field that matches one of these parts and a 'name' field that
    matches the remaining part with a threshold Levenshtein similarity.

    Args:
        spotify (spotipy.Spotify): spotify client
        title (str): submission title

    Returns:
        ([(str, str), ...]): list of Spotify track ('id', 'name') tuples
    """
    title, artist = parse_title(title)
    if not (title and artist):
        return []

    results = spotify.search(
            q=f"{title.replace(' ', '+')}+{artist.replace(' ', '+')}",
            type='track', limit=50)

    match = filter_results(spotify, results, threshold, title, artist)
    if match:
        return (match['id'], f"{match['name']} - " \
                f"{', '.join([y['name'] for y in match['artists']])}")
    return None


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
    tracks = filter_tracks(results['tracks']['items'], threshold, title,
                           artist)
    while results['tracks']['next']:
        try:
            results = spotify.next(results['tracks'])
        except Exception:
            logger.warning(f"Failed to get next tracks: {format_exc()}")
            break
        tracks.extend(filter_tracks(results['tracks']['items'], threshold,
                                    title, artist))

    if tracks:
        track, _ = sorted(tracks, key=itemgetter(1)).pop()

        return track


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
    results = []
    for track in tracks:
        artists = {x['name'].lower() for x in track['artists']}
        title_match = max(fuzz.ratio(track['name'].lower(), title.lower()),
                          fuzz.ratio(track['name'].lower(), artist.lower()))
        if title_match >= threshold:
            if any((fuzz.ratio(a, part) >= threshold
                    for part in [title.lower(), artist.lower()]
                    for a in artists)):
                results.append((track, title_match))

    return results


def update_existing_playlist(spotify, playlist, new_tracks, limit, verbosity):
    """Adds new tracks to an existing playlist; removes old tracks if adding
    new track causes playlist count to surpass 'limit'.

    Args:
        spotify (spotipy.Spotify): spotify client
        playlist (str): Spotify playlist ID
        new_tracks (list): list of spotipy.Track objects

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
    add_payload = []
    tracks_added = []
    remove_payload = []
    tracks_removed = []
    ids = set()
    playlist_track_names = set()
    for track in tracks:
        track = track['track']
        ids.add(track['id'])
        playlist_track_names.add(f"{track['name']} - " \
                f"{', '.join([x['name'] for x in track['artists']])}")

    for id_, track in new_tracks:
        if 'spotify.com/track/' in id_:
            resp = spotify.track(id_)
            id_ = resp['id']
            track = f"{resp['name']} - " \
                    f"{', '.join([x['name'] for x in resp['artists']])}"
        if id_ in ids:
            logger.warning(f'Candidate new track "{track}" is already in ' \
                           'the playlist')
            continue
        if track_name_too_similar(track, playlist_track_names):
            continue
        tracks_added.append(track)
        add_payload.append(id_)
        if track_count + len(tracks_added) > limit:
            _track = tracks.pop(0)['track']
            tracks_removed.append(f"{_track['name']} - " \
                    f"{', '.join([x['name'] for x in _track['artists']])}")
            remove_payload.append({"uri": _track['uri'],
                                   "positions": [track_index]})
            track_index += 1
            track_count -= 1

    logger.info(f"{len(tracks_added)} new tracks added")
    if tracks_added:
        if verbosity > 0:
            for track in tracks_added:
                logger.info(f"\t{track}")

    logger.info(f"{len(tracks_removed)} old tracks removed")
    if tracks_removed:
        if verbosity > 0:
            for track in tracks_removed:
                logger.info(f"\t{track}")

    if remove_payload:
        spotify.playlist_remove_specific_occurrences_of_items(playlist,
                                                              remove_payload)
    if add_payload:
        spotify.playlist_add_items(playlist, add_payload)

    return _playlist


def track_name_too_similar(track, playlist_track_names):
    """Fuzzy matches candidate new track with tracks already in playlist to see
    if it's a duplicate.

    Args:
        track (str): track title - artist name of candidate new track
        playlist_track_names (set): track title - artist names in playlist

    Returns:
        bool: whether or not any tracks in the playlist are too similar
    """
    for other_track in playlist_track_names:
        if fuzz.ratio(track.lower(), other_track.lower()) > 90:
            logger.warning(f'Candidate new track "{track}" is too similar ' \
                           f'to existing track "{other_track}"')
            return True
    return False


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
