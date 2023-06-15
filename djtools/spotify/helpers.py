"""This module contains helper functions used by the "spotify" module."""
from concurrent.futures import ThreadPoolExecutor
import logging
from operator import itemgetter
from pathlib import Path
import sys
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Tuple, Union

import asyncpraw as praw
from fuzzywuzzy import fuzz
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tqdm import tqdm
import yaml

from djtools.configs.config import BaseConfig


logger = logging.getLogger(__name__)


def build_new_playlist(
    spotify: spotipy.Spotify,
    username: str,
    subreddit: str,
    new_tracks: List[Tuple[str]],
) -> Dict[str, Any]:
    """Creates a new playlist from a list of track IDs / URLs.

    Args:
        spotify: Spotify client.
        username: Spotify username.
        subreddit: Subreddit name to filter.
        new_tracks: List of Spotify track ("id", "name") tuples.

    Returns:
        Playlist object for the newly constructed playlist.
    """
    ids = list(zip(*new_tracks))[0]
    playlist = spotify.user_playlist_create(
        username, name=f"{subreddit.title()}"
    )
    spotify.playlist_add_items(playlist["id"], ids, position=None)

    return playlist


async def catch(generator: AsyncGenerator, message: Optional[str] = "") -> Any:
    """This function permits one-line try/except logic for comprehensions.

    Args:
        generator: Async generator.
        message: Prefix message for logger warning.

    Returns:
        Return of the AsyncGenerator.
    """
    while True:
        try:
            yield await generator.__anext__()
        except StopAsyncIteration:
            return
        except Exception as exc:
            logger.warning(f"{message}: {exc}" if message else exc)
            continue


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
    track, dist = {}, 0.0
    tracks = filter_tracks(
        results["tracks"]["items"], threshold, title, artist
    )
    while results["tracks"]["next"]:
        try:
            results = spotify.next(results["tracks"])
        except Exception:
            logger.warning(f"Failed to get next tracks for {title, artist}")
            break
        tracks.extend(
            filter_tracks(results["tracks"]["items"], threshold, title, artist)
        )

    if tracks:
        track, dist = max(tracks, key=itemgetter(1))

    return track, dist


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
    artist = ", ".join(sorted([x.strip() for x in artist.split(",")]))
    for track in tracks:
        artists = ", ".join(
            sorted({x["name"].lower() for x in track["artists"]})
        )
        title_match = max(
            fuzz.ratio(track["name"].lower(), title.lower()),
            fuzz.ratio(track["name"].lower(), artist.lower())
        )
        artist_match = max(
            fuzz.ratio(artists.lower(), title.lower()),
            fuzz.ratio(artists.lower(), artist.lower()),
        )
        if title_match >= threshold and artist_match >= threshold:
            results.append((track, title_match + artist_match))

    return results


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
    ret = None
    parts = parse_title(title)
    if not all(parts):
        return ret

    matches = []
    for track, artist in [parts, parts[::-1]]:
        try:
            results = spotify.search(
                q=f"track:{track} artist:{artist}",
                type="track",
                limit=50,
            )
        except Exception as exc:
            logger.error(f'Error searching for "{track} - {artist}": {exc}')
            continue

        artist = ", ".join(sorted([x.strip() for x in artist.split(",")]))
        match, dist = filter_results(spotify, results, threshold, track, artist)
        if match:
            artists = ", ".join([y["name"] for y in match["artists"]])
            matches.append((dist, match["id"], f'{match["name"]} - {artists}'))

    if matches:
        ret = tuple(max(matches, key=itemgetter(0))[1:])

    return ret


def get_playlist_ids() -> Dict[str, str]:
    """Load Spotify playlist names -> IDs lookup.

    Returns:
        Dictionary of Spotify playlist names mapped to playlist IDs. 
    """
    playlist_ids = {}
    ids_path = Path(__file__).parent.parent / "configs" / "spotify_playlists.yaml"
    if ids_path.exists():
        with open(ids_path, mode="r", encoding="utf-8") as _file:
            playlist_ids = yaml.load(_file, Loader=yaml.FullLoader) or {}

    return playlist_ids


def get_reddit_client(config: BaseConfig) -> praw.Reddit:
    """Instantiate a Reddit API client.

    Args:
        config: Configuration object.

    Returns:
        Reddit API client.
    """
    reddit = praw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        user_agent=config.REDDIT_USER_AGENT,
        timeout=30,
    )

    return reddit


def get_spotify_client(config: BaseConfig) -> spotipy.Spotify:
    """Instantiate a Spotify API client.

    Args:
        config: Configuration object.

    Returns:
        Spotify API client.
    """
    spotify = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=config.SPOTIFY_CLIENT_ID,
            client_secret=config.SPOTIFY_CLIENT_SECRET,
            redirect_uri=config.SPOTIFY_REDIRECT_URI,
            scope="playlist-modify-public",
            requests_timeout=30,
            cache_handler=spotipy.CacheFileHandler(
                cache_path=Path(__file__).parent / ".spotify.cache"
            ),
        )
    )

    return spotify


async def get_subreddit_posts(
    spotify: spotipy.Spotify,
    reddit: praw.Reddit,
    subreddit: Dict[str, Union[str, int]],
    config: BaseConfig,
    praw_cache: Dict[str, bool],
) -> Tuple[List[Tuple[str]], Dict[str, Union[str, int]]]:
    """Filters the submissions for the provided subreddit and tries to resolve
        each into a Spotify track until all the submissions are parsed or the
        track limit has been met.

    Args:
        spotify: Spotify client.
        reddit: Reddit client.
        subreddit: SubredditConfig object as a dictionary.
        config: Configuration object.
        praw_cache: Cached praw submissions.

    Returns:
        List of Spotify track ("id", "name") tuples and SubredditConfig as a
            dictionary.
    """
    sub = await reddit.subreddit(subreddit["name"])
    func = getattr(sub, subreddit["type"])
    kwargs = {"limit": config.SPOTIFY_PLAYLIST_POST_LIMIT}
    if subreddit["type"]== "top":
        kwargs["time_filter"] = subreddit["period"]
    subs = [
        x async for x in catch(
            func(**kwargs), message="Failed to retrieve Reddit submission"
        )
    ]
    msg = f'Filtering {len(subs)} "r/{subreddit["name"]}" {subreddit["type"]} posts'
    logger.info(msg)
    submissions = []
    for submission in tqdm(subs, desc=msg):
        if submission.id in praw_cache:
            continue
        submissions.append(submission)
        praw_cache[submission.id] = True
    new_tracks = []
    if submissions:
        msg = (
            f"Searching Spotify for {len(submissions)} new submission(s) from "
            f'"r/{subreddit["name"]}"'
        )
        logger.info(msg)
        payload = [
            submissions,
            [spotify] * len(submissions),
            [config.SPOTIFY_PLAYLIST_FUZZ_RATIO] * len(submissions)
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


def parse_title(title: str) -> List[str]:
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
            return [None, None]

    title, artist = map(str.strip, [title.split("(")[0], artist.split("(")[0]])
    title, artist = map(str.strip, [title.split("[")[0], artist.split("[")[0]])

    return [title, artist]


def populate_playlist(
    playlist_name: str,
    playlist_ids: Dict[str, str],
    spotify_username: str,
    spotify: spotipy.Spotify,
    tracks: List[Tuple[str]],
    playlist_limit: Optional[int] = sys.maxsize,
    verbosity: Optional[int] = 0,
) -> Dict[str, str]:
    """Inserts tracks into either a new playlist or an existing one.

    Args:
        playlist_name: Name of the playlist.
        playlist_ids: Lookup of playlist IDs.
        spotify_username: Spotify user's username.
        spotify: Spotify client.
        tracks: List of tracks.
        playlist_limit: Maximum number of tracks allowed in a playlist.
        verbosity: Logging verbosity level.

    Returns:
        Updated playlist IDs.
    """
    playlist_id = playlist_ids.get(playlist_name)
    playlist = None
    if playlist_id and tracks:
        playlist = update_existing_playlist(
            spotify,
            playlist_id,
            tracks,
            playlist_limit,
            verbosity,
        )
    elif tracks:
        logger.warning(
            f'Unable to get ID for {playlist_name}...creating a new '
            "playlist"
        )
        playlist = build_new_playlist(
            spotify, spotify_username, playlist_name, tracks
        )
        playlist_ids[playlist_name] = playlist["id"]
    elif playlist_id:
        playlist = spotify.playlist(playlist_id)
    if playlist:
        logger.info(
            f'"{playlist["name"]}": '
            f'{playlist["external_urls"].get("spotify")}'
        )

    return playlist_ids


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


def write_playlist_ids(playlist_ids: Dict[str, str]):
    """Write playlist IDs to file.

    Args:
        playlist_ids: Dictionary of Spotify playlist names mapped to playlist
            IDs. 
    """
    ids_path = (
        Path(__file__).parent.parent / "configs" / "spotify_playlists.yaml"
    )
    with open(ids_path, mode="w", encoding="utf-8") as _file:
        yaml.dump(playlist_ids, _file)
