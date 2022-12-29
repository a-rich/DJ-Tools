"""This module is responsible for creating or updating Spotify playlists by
querying subreddit posts. Posts are first checked to see if they are direct
links to a Spotify track. If this is not the case, then the post title is
parsed in an attempt to interpret it as either 'ARTIST NAME - TRACK TITLE' or
'TRACK TITLE - ARTIST NAME'. These components are then used to search the
Spotify API for tracks. The resulting tracks have their title and artist fields
compared with the reddit post title and are added to the respective playlist
if the Levenshtein similarity passes a threshold.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import inspect
import json
import logging
from operator import itemgetter
import os
from traceback import format_exc
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import asyncpraw as praw
from fuzzywuzzy import fuzz
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tqdm import tqdm

from djtools.utils.helpers import catch, raise_


# Silence PRAW, Spotify, and urllib3 loggers.
for logger in ["asyncprawcore", "spotipy", "urllib3"]:
    logger = logging.getLogger(logger)
    logger.setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def update_auto_playlists(
    config: Dict[str, Union[List, Dict, str, bool, int, float]]
):
    """This helper function asynchronously updates Spotify playlists.

    Args:
        config: Configuration object.
    """
    asyncio.run(async_update_auto_playlists(config))


async def async_update_auto_playlists(
    config: Dict[str, Union[List, Dict, str, bool, int, float]]
):
    """This function updates the contents of one or more Spotify playlists with
        the posts of one or more subreddits (currently only supports one
        subreddit per playlist).

    Args:
        config: Configuration object.
    
    Raises:
        KeyError: "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", and
            "SPOTIFY_REDIRECT_URI" must be configured.
        KeyError: "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", and
            "REDDIT_USER_AGENT" must be configured.
        KeyError: "SPOTIFY_USERNAME" must be configured.
    """
    if not config.get("AUTO_PLAYLIST_SUBREDDITS"):
        logger.error(
            "Using the spotify_playlist_builder module requires the config "
            "option AUTO_PLAYLIST_SUBREDDITS"
        )
        return

    try:
        spotify = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=config["SPOTIFY_CLIENT_ID"],
                client_secret=config["SPOTIFY_CLIENT_SECRET"],
                redirect_uri=config["SPOTIFY_REDIRECT_URI"],
                scope="playlist-modify-public",
                requests_timeout=30,
                cache_handler=spotipy.CacheFileHandler(
                    cache_path=os.path.join(
                        os.path.dirname(__file__), ".spotify.cache"
                    ).replace(os.sep, "/"),
                ),
            )
        )
    except KeyError:
        raise KeyError(
            "Using the spotify_playlist_builder module requires the following "
            "config options: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, "
            "SPOTIFY_REDIRECT_URI"
        ) from KeyError 
    except Exception as exc:
        raise Exception(f"Failed to instantiate the Spotify client: {exc}")

    try:
        reddit = praw.Reddit(
            client_id=config["REDDIT_CLIENT_ID"],
            client_secret=config["REDDIT_CLIENT_SECRET"],
            user_agent=config["REDDIT_USER_AGENT"],
            timeout=30,
        )
    except KeyError:
        raise KeyError(
            "Using the spotify_playlist_builder module requires the following "
            "config options: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, "
            "REDDIT_USER_AGENT"
        ) from KeyError

    subreddit_playlist_ids = {}
    ids_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "configs",
        "playlist_builder.json",
    ).replace(os.sep, "/")
    if os.path.exists(ids_path):
        with open(ids_path, mode="r", encoding="utf-8") as _file:
            subreddit_playlist_ids = json.load(_file)
    
    praw_cache = {}
    cache_file = os.path.join(
        os.path.dirname(__file__), ".praw.cache"
    ).replace(os.sep, "/")
    if os.path.exists(cache_file):
        with open(cache_file, mode="r", encoding="utf-8") as _file:
            praw_cache = json.load(_file)
    
    tasks = []
    for subreddit in config["AUTO_PLAYLIST_SUBREDDITS"]:
        playlist_id = subreddit_playlist_ids.get(subreddit["name"])
        if not playlist_id:
            try:
                username = config["SPOTIFY_USERNAME"]
            except KeyError:
                raise KeyError(
                    "Building a new playlist in the spotify_playlist_builder "
                    "module requires the config option SPOTIFY_USERNAME"
                ) from KeyError
        tasks.append(
            asyncio.create_task(
                get_subreddit_posts(
                    spotify,
                    reddit,
                    subreddit,
                    config,
                    praw_cache,
                )
            )
        )

    for task in asyncio.as_completed(tasks):
        tracks, subreddit = await task
        playlist_id = subreddit_playlist_ids.get(subreddit["name"])
        playlist = None
        if playlist_id and tracks:
            playlist = update_existing_playlist(
                spotify,
                playlist_id,
                tracks,
                subreddit["limit"],
                config.get("VERBOSITY", 0),
            )
        elif tracks:
            logger.warning(
                f'Unable to get ID for {subreddit["name"]}...creating a new '
                "playlist"
            )
            playlist = build_new_playlist(
                spotify, username, subreddit["name"], tracks
            )
            subreddit_playlist_ids[subreddit["name"]] = playlist["id"]
        elif playlist_id:
            playlist = spotify.playlist(playlist_id)
        if playlist:
            logger.info(
                f'"{playlist["name"]}": '
                f'{playlist["external_urls"].get("spotify")}'
            )
    
    await reddit.close()

    with open(ids_path, mode="w", encoding="utf-8") as _file:
        json.dump(subreddit_playlist_ids, _file, indent=2)

    with open(cache_file, mode="w", encoding="utf-8") as _file:
        json.dump(praw_cache, _file)


async def get_subreddit_posts(
    spotify: spotipy.Spotify,
    reddit: praw.Reddit,
    subreddit: Dict[str, Union[str, int]],
    config: Dict[str, Union[List, Dict, str, bool, int, float]],
    praw_cache: Dict[str, bool],
) -> Tuple[List[Tuple[str]], Dict[str, Union[str, int]]]:
    """Filters the submissions for the provided subreddit and tries to resolve
        each into a Spotify track until all the submissions are parsed or the
        track limit has been met.

    Args:
        spotify: Spotify client.
        reddit: Reddit client.
        subreddit: "name", "type", "period", and "limit".
        config: Configuration object.
        praw_cache: Cached praw submissions.
    
    Raises:
        AttributeError: "type" must match a method of the "Subreddit" class.

    Returns:
        List of Spotify track ("id", "name") tuples and subreddit config dict.
    """
    sub_limit = config.get("AUTO_PLAYLIST_SUBREDDIT_LIMIT", 500) or None
    sub = await reddit.subreddit(subreddit["name"])
    try:
        func = getattr(sub, subreddit["type"])
    except AttributeError:
        raise AttributeError(
            f'Method "{subreddit["type"]}" does not exist in "Subreddit" class'
        ) from AttributeError
    if subreddit["type"] == "top":
        subs = [
            x async for x in catch(
                func,
                handle=lambda exc: raise_(exc)
                    if isinstance(exc, TypeError) else logger.info(exc),
                limit=sub_limit,
                time_filter=subreddit["period"],
            )
        ]
    else:
        subs = [
            x async for x in catch(
                func,
                handle=lambda exc: logger.info(exc),
                limit=sub_limit,
            )
        ]
    msg = (
        f'Filtering {len(subs)} "r/{subreddit["name"]}" {subreddit["type"]} '
        "posts"
    )
    logger.info(msg)
    submissions = []
    for submission in tqdm(subs, desc=msg):
        if submission.id in praw_cache:
            continue
        submissions.append(submission)
        praw_cache[submission.id] = True
    new_tracks = []
    if len(submissions):
        msg = (
            f"Searching Spotify for {len(submissions)} new submission(s) from "
            f'"r/{subreddit["name"]}"'
        )
        logger.info(msg)
        payload = [
            submissions,
            [spotify] * len(submissions),
            [config.get("AUTO_PLAYLIST_FUZZ_RATIO", 50)] * len(submissions)
        ]
        with ThreadPoolExecutor(max_workers=8) as executor:
            new_tracks = list(
                tqdm(
                    executor.map(process, *payload),
                    total=len(submissions),
                    desc=msg,
                )
            )
        new_tracks = [track for track in new_tracks if track]
        logger.info(
            f"Got {len(new_tracks)} Spotify track(s) from new "
            f'"r/{subreddit["name"]}" posts'
        )
    else:
        logger.info(f'No new submissions from "r/{subreddit["name"]}"')

    return new_tracks, subreddit


def process(
    submission: praw.models.Submission,
    spotify: spotipy.Spotify,
    threshold: float,
) -> Tuple[str]:
    """Worker thread process.

    Args:
        submission: Submission object.
        spotify: Spotify API client.
        threshold: Minimum Levenshtein distance.

    Returns:
        Tuple of matching track's ID and artist - title.
    """
    if "spotify.com/track/" in submission.url:
        return (submission.url, submission.title)

    return fuzzy_match(spotify, submission.title, threshold)


def fuzzy_match(
    spotify: spotipy.Spotify, title: str, threshold: float
) -> Optional[Tuple[str]]:
    """Attempts to split submission title into two parts
        (track name, artist(s)), search Spotify for tracks that have an
        "artist" field that matches one of these parts and a "name" field that
        matches the remaining part with a threshold Levenshtein similarity.

    Args:
        spotify: Spotify client.
        title: Submission title.
        threshold: Minimum Levenshtein distance.

    Returns:
        Tuple of matching track's ID and artist - title or None if no match.
    """
    title, artist = parse_title(title)
    if not (title and artist):
        return

    try:
        results = spotify.search(
            q=f'{title.replace(" ", "+")}+{artist.replace(" ", "+")}',
            type="track",
            limit=50,
        )
    except Exception as exc:
        logger.error(f'Error searching for "{title} - {artist}": {exc}')
        return

    match = filter_results(spotify, results, threshold, title, artist)
    if match:
        artists = ", ".join([y["name"] for y in match["artists"]])
        return match["id"], f'{match["name"]} - {artists}'

    return


def parse_title(title: str) -> Tuple[str]:
    """Attempts to split submission title into two parts
        (track name, artist(s)).

    Args:
        title: Submission title.

    Returns:
        Pair of strings that represent (in no particular order) the artist(s)
            and track name(s).
    """
    try:
        title, artist = map(str.strip, title.split(" - "))
    except ValueError:
        try:
            title, artist = map(str.strip, title.lower().split(" by "))
        except ValueError:
            return None, None

    title, artist = map(str.strip, [title.split("(")[0], artist.split("(")[0]])
    title, artist = map(str.strip, [title.split("[")[0], artist.split("[")[0]])

    return title, artist


def filter_results(
    spotify: spotipy.Spotify,
    results: List[Dict],
    threshold: float,
    title: str,
    artist: str,
) -> Tuple[Dict[str, Any], float]:
    """Helper function for applying filtering logic to find tracks that
        match the submission title closely enough.

    Args:
        spotify: Spotify client.
        results: Spotify search results.
        threshold: Minimum Levenshtein distance.
        title: Potential title of a track.
        artist: Potential artist of a track.

    Returns:
        Tuple of track object and Levenshtein distance. 
    """
    tracks = filter_tracks(
        results["tracks"]["items"], threshold, title, artist
    )
    while results["tracks"]["next"]:
        try:
            results = spotify.next(results["tracks"])
        except Exception:
            logger.warning(f"Failed to get next tracks: {format_exc()}")
            break
        tracks.extend(
            filter_tracks(results["tracks"]["items"], threshold, title, artist)
        )

    if tracks:
        track, _ = sorted(tracks, key=itemgetter(1)).pop()

        return track


def filter_tracks(
    tracks: Dict, threshold: float, title: str, artist: str
) -> List[Tuple[Dict[str, Any], float]]:
    """Applies Levenshtein distance filtering on both the resulting
        tracks' "artist" and "name" fields to qualify a match for the
        submission title.

    Args:
        tracks: Spotify search results.
        threshold: Minimum Levenshtein distance.
        title: Potential title of a track.
        artist: Potential artist of a track.

    Returns:
        List of tuple of track object and Levenshtein distance. 
    """
    results = []
    for track in tracks:
        artists = {x["name"].lower() for x in track["artists"]}
        title_match = max(
            fuzz.ratio(track["name"].lower(), title.lower()),
            fuzz.ratio(track["name"].lower(), artist.lower())
        )
        if title_match >= threshold:
            if any(
                fuzz.ratio(a, part) >= threshold
                for part in [title.lower(), artist.lower()] for a in artists
            ):
                results.append((track, title_match))

    return results


def update_existing_playlist(
    spotify: spotipy.Spotify,
    playlist: str,
    new_tracks: str,
    limit: int,
    verbosity: int,
) -> Dict[str, Any]:
    """Adds new tracks to an existing playlist; removes old tracks if adding
        new track causes playlist count to surpass "limit".

    Args:
        spotify: Spotify client.
        playlist: Spotify playlist ID.
        new_tracks: List of (Spotify track IDs, track names).
        limit: Maximum number of tracks to add.
        verbosity: Verbosity level.

    Returns:
        Playlist object for the newly constructed playlist.
    """
    _playlist = spotify.playlist(playlist)
    tracks = _playlist["tracks"]["items"]
    while _playlist["tracks"]["next"]:
        _playlist = spotify.next(_playlist["tracks"])
        tracks.extend(_playlist["tracks"]["items"])

    track_count = len(tracks)
    track_index = 0
    add_payload = []
    tracks_added = []
    remove_payload = []
    tracks_removed = []
    ids = set()
    playlist_track_names = set()
    for track in tracks:
        track = track["track"]
        ids.add(track["id"])
        artists = ", ".join([x["name"] for x in track["artists"]])
        playlist_track_names.add(f'{track["name"]} - {artists}')

    for id_, track in new_tracks:
        if "spotify.com/track/" in id_:
            resp = spotify.track(id_)
            id_ = resp["id"]
            artists = ", ".join([x["name"] for x in resp["artists"]])
            track = f'{resp["name"]} - {artists}'
        if id_ in ids:
            logger.warning(
                f'Candidate new track "{track}" is already in the playlist'
            )
            continue
        if track_name_too_similar(track, playlist_track_names):
            continue
        tracks_added.append(track)
        add_payload.append(id_)
        if track_count + len(tracks_added) > limit:
            _track = tracks.pop(0)["track"]
            artists = ", ".join([x["name"] for x in _track["artists"]])
            tracks_removed.append(f'{_track["name"]} - {artists}')
            remove_payload.append(
                {"uri": _track["uri"], "positions": [track_index]}
            )
            track_index += 1
            track_count -= 1

    if tracks_added:
        logger.info(f"{len(tracks_added)} new tracks added")
        if verbosity > 0:
            for track in tracks_added:
                logger.info(f"\t{track}")

    if tracks_removed:
        logger.info(f"{len(tracks_removed)} old tracks removed")
        if verbosity > 0:
            for track in tracks_removed:
                logger.info(f"\t{track}")
    
    if not (tracks_added or tracks_removed):
        logger.info("No tracks added or removed")

    if remove_payload:
        spotify.playlist_remove_specific_occurrences_of_items(playlist,
                                                              remove_payload)
    if add_payload:
        spotify.playlist_add_items(playlist, add_payload)

    return _playlist


def track_name_too_similar(track: str, playlist_track_names: Set[str]) -> bool:
    """Fuzzy matches candidate new track with tracks already in playlist to see
        if it's a duplicate.

    Args:
        track: Track title - artist name of candidate new track.
        playlist_track_names: Track title - artist names in playlist.

    Returns:
        Whether or not any tracks in the playlist are too similar.
    """
    for other_track in playlist_track_names:
        if fuzz.ratio(track.lower(), other_track.lower()) > 90:
            logger.warning(
                f'Candidate new track "{track}" is too similar to existing '
                f'track "{other_track}"'
            )
            return True

    return False


def build_new_playlist(
    spotify: spotipy.Spotify,
    username: str,
    subreddit: Dict[str, Union[str, int]],
    new_tracks: List[Tuple[str]],
) -> Dict[str, Any]:
    """Creates a new playlist from a list of track IDs / URLs.

    Args:
        spotify: Spotify client.
        subreddit: Subreddit name to filter.
        new_tracks: List of Spotify track ("id", "name") tuples.

    Returns:
        Playlist object for the newly constructed playlist.
    """
    ids = list(zip(*new_tracks))[0]
    playlist = spotify.user_playlist_create(
        username, name=f"r/{subreddit.title()}"
    )
    spotify.playlist_add_items(playlist["id"], ids, position=None)

    return playlist
