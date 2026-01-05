"""This module contains helper functions used by the spotify module.

Most of the heavy lifting is now delegated to the spotify-tools library.
This module provides DJ-Tools specific wrappers and configuration handling.
"""

import logging
from pathlib import Path
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

import asyncpraw as praw
import yaml

from spotify_tools import (
    Client,
    SpotifyConfig,
    filter_tracks_by_similarity,
    is_duplicate_track,
    search_track_fuzzy,
)


logger = logging.getLogger(__name__)
BaseConfig = Type["BaseConfig"]
DJToolsSpotifyConfig = Type["SpotifyConfig"]
SubredditConfig = Type["SubredditConfig"]


def get_playlist_ids() -> Dict[str, str]:
    """Load Spotify playlist names -> IDs lookup.

    Returns:
        Dictionary of Spotify playlist names mapped to playlist IDs.
    """
    playlist_ids = {}
    ids_path = (
        Path(__file__).parent.parent / "configs" / "spotify_playlists.yaml"
    )
    if ids_path.exists():
        with open(ids_path, mode="r", encoding="utf-8") as _file:
            playlist_ids = (
                yaml.load(_file, Loader=yaml.FullLoader) or playlist_ids
            )

    return playlist_ids


def get_reddit_client(config: BaseConfig) -> praw.Reddit:
    """Instantiate a Reddit API client.

    Args:
        config: Configuration object.

    Returns:
        Reddit API client.
    """
    reddit = praw.Reddit(
        client_id=config.spotify.reddit_client_id,
        client_secret=config.spotify.reddit_client_secret,
        user_agent=config.spotify.reddit_user_agent,
        timeout=30,
    )

    return reddit


def get_spotify_client(
    config: Union[BaseConfig, DJToolsSpotifyConfig],
) -> Client:
    """Instantiate a Spotify API client using spotify-tools.

    Args:
        config: Configuration object.

    Returns:
        Spotify API client.
    """
    try:
        spotify_config = getattr(config, "spotify")
    except AttributeError:
        spotify_config = config

    st_config = SpotifyConfig(
        CLIENT_ID=spotify_config.spotify_client_id,
        CLIENT_SECRET=spotify_config.spotify_client_secret,
        REDIRECT_URI=spotify_config.spotify_redirect_uri,
    )

    return Client(
        config=st_config,
        scopes=["playlist-modify-public"],
        cache_path=Path(__file__).parent / ".spotify.cache",
    )


def filter_results(
    spotify: Client,
    results: Dict,
    threshold: float,
    title: str,
    artist: str,
) -> Tuple[Dict[str, Any], float]:
    """Filter Spotify search results to find best matching track.

    Args:
        spotify: Spotify client.
        results: Spotify search results.
        threshold: Minimum Levenshtein distance.
        title: Potential title of a track.
        artist: Potential artist of a track.

    Returns:
        Tuple of track object (as dict) and similarity score.
    """
    # Convert spotify-tools Track objects to dicts for backward compatibility
    tracks = results.get("tracks", {}).get("items", [])

    # Use spotify-tools filtering
    from spotify_tools.schemas import Track

    track_objects = [Track.model_validate(t) for t in tracks if t]

    matches = filter_tracks_by_similarity(
        track_objects, title, artist, threshold
    )

    # Paginate through remaining results
    while results.get("tracks", {}).get("next"):
        try:
            results = spotify.next(results["tracks"])
            if not results:
                break
            tracks = results.get("tracks", {}).get("items", [])
            if not tracks:
                tracks = results.get("items", [])
            track_objects = [Track.model_validate(t) for t in tracks if t]
            matches.extend(
                filter_tracks_by_similarity(
                    track_objects, title, artist, threshold
                )
            )
        except Exception:
            logger.warning(f"Failed to get next tracks for {title, artist}")
            break

    if not matches:
        return {}, 0.0

    best = max(matches, key=lambda m: m.score)
    # Convert back to dict format for backward compatibility
    return best.track.model_dump(), best.score


async def get_subreddit_posts(
    spotify: Client,
    reddit: praw.Reddit,
    subreddit: SubredditConfig,
    config: BaseConfig,
    praw_cache: Dict[str, bool],
) -> Tuple[List[Tuple[str]], Dict[str, Union[str, int]]]:
    """Filters subreddit submissions and resolves them to Spotify tracks.

    Args:
        spotify: Spotify client.
        reddit: Reddit client.
        subreddit: SubredditConfig object.
        config: Configuration object.
        praw_cache: Cached praw submissions.

    Returns:
        List of Spotify track ("id", "name") tuples and SubredditConfig.
    """
    from concurrent.futures import as_completed, ThreadPoolExecutor
    from tqdm import tqdm

    sub = await reddit.subreddit(subreddit.name)
    func = getattr(sub, subreddit.type.value)
    kwargs = {"limit": config.spotify.spotify_playlist_post_limit}
    from djtools.spotify.enums import SubredditType

    if subreddit.type == SubredditType.TOP:
        kwargs["time_filter"] = subreddit.period

    subs = [
        x
        async for x in _catch(
            func(**kwargs), message="Failed to retrieve Reddit submission"
        )
    ]

    msg = f'Filtering {len(subs)} "r/{subreddit.name}" {subreddit.type.value} posts'
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
            f'"r/{subreddit.name}"'
        )
        logger.info(msg)
        payload = zip(
            submissions,
            [spotify] * len(submissions),
            [config.spotify.spotify_playlist_fuzz_ratio] * len(submissions),
        )

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(_process, *args) for args in payload]

            with tqdm(total=len(futures), desc=msg) as pbar:
                new_tracks = []
                for future in as_completed(futures):
                    new_tracks.append(future.result())
                    pbar.update(1)

        new_tracks = [track for track in new_tracks if track]
        logger.info(
            f"Got {len(new_tracks)} Spotify track(s) from new "
            f'"r/{subreddit.name}" posts'
        )
    else:
        logger.info(f'No new submissions from "r/{subreddit.name}"')

    return new_tracks, subreddit


def populate_playlist(
    playlist_name: str,
    playlist_ids: Dict[str, str],
    spotify_username: str,
    spotify: Client,
    tracks: List[Tuple[str]],
    playlist_limit: Optional[int] = None,
    verbosity: Optional[int] = 0,
) -> Dict[str, str]:
    """Inserts tracks into either a new playlist or an existing one.

    Args:
        playlist_name: Name of the playlist.
        playlist_ids: Lookup of playlist IDs.
        spotify_username: Spotify user's username.
        spotify: Spotify client.
        tracks: List of (track_id, track_name) tuples.
        playlist_limit: Maximum number of tracks allowed in a playlist.
        verbosity: Logging verbosity level.

    Returns:
        Updated playlist IDs.
    """
    playlist_id = playlist_ids.get(playlist_name)
    playlist = None

    if playlist_id and tracks:
        playlist = _update_existing_playlist(
            spotify,
            playlist_id,
            tracks,
            playlist_limit,
            verbosity,
        )
    elif tracks:
        logger.warning(
            f"Unable to get ID for {playlist_name}...creating a new playlist"
        )
        playlist = _build_new_playlist(
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


def _build_new_playlist(
    spotify: Client,
    username: str,
    playlist_name: str,
    new_tracks: List[Tuple[str]],
) -> Dict[str, Any]:
    """Creates a new playlist from a list of track IDs / URLs.

    Args:
        spotify: Spotify client.
        username: Spotify username.
        playlist_name: Name for the new playlist.
        new_tracks: List of (track_id, track_name) tuples.

    Returns:
        Playlist object for the newly constructed playlist.
    """
    ids = [t[0] for t in new_tracks]
    playlist = spotify.user_playlist_create(
        username, name=playlist_name.title()
    )
    spotify.playlist_add_items(playlist["id"], ids)

    return playlist


async def _catch(
    generator: AsyncGenerator, message: Optional[str] = ""
) -> Any:
    """Permits one-line try/except logic for async comprehensions.

    Args:
        generator: Async generator.
        message: Prefix message for logger warning.

    Yields:
        Items from the AsyncGenerator.
    """
    while True:
        try:
            yield await anext(generator)
        except StopAsyncIteration:
            return
        except Exception as exc:
            logger.warning(f"{message}: {exc}" if message else exc)
            continue


def _filter_tracks(
    tracks: List[Dict], threshold: float, title: str, artist: str
) -> List[Tuple[Dict[str, Any], float]]:
    """Filter tracks by Levenshtein distance on artist and name fields.

    Args:
        tracks: Spotify search results.
        threshold: Minimum Levenshtein distance.
        title: Potential title of a track.
        artist: Potential artist of a track.

    Returns:
        List of (track_dict, similarity_score) tuples.
    """
    from spotify_tools.schemas import Track

    track_objects = [Track.model_validate(t) for t in tracks if t]
    matches = filter_tracks_by_similarity(
        track_objects, title, artist, threshold
    )
    return [(m.track.model_dump(), m.score) for m in matches]


def _fuzzy_match(
    spotify: Client, title: str, threshold: float
) -> Optional[Tuple[str, str]]:
    """Attempts to find a Spotify track matching the title.

    Args:
        spotify: Spotify client.
        title: Submission title.
        threshold: Minimum Levenshtein distance.

    Returns:
        Tuple of (track_id, "track_name - artists") or None.
    """
    parts = _parse_title(title)
    if not all(parts):
        return None

    # Try both orderings (title-artist and artist-title)
    for track, artist in [parts, parts[::-1]]:
        try:
            result = search_track_fuzzy(
                spotify, track, artist, threshold=threshold, limit=50
            )
            if result and result.track:
                track_obj = result.track
                artists = ", ".join(
                    a.name for a in (track_obj.artists or []) if a.name
                )
                return (track_obj.id, f"{track_obj.name} - {artists}")
        except Exception as exc:
            logger.error(f'Error searching for "{track} - {artist}": {exc}')
            continue

    return None


def _parse_title(title: str) -> List[str]:
    """Attempts to split submission title into (track name, artist(s)).

    Args:
        title: Submission title.

    Returns:
        Pair of strings: [title, artist] or [None, None] if unparseable.
    """
    try:
        title_part, artist = map(str.strip, title.split(" - "))
    except ValueError:
        try:
            title_part, artist = map(str.strip, title.lower().split(" by "))
        except ValueError:
            return [None, None]

    # Remove parenthetical and bracketed content
    title_part = title_part.split("(")[0].strip()
    title_part = title_part.split("[")[0].strip()
    artist = artist.split("(")[0].strip()
    artist = artist.split("[")[0].strip()

    return [title_part, artist]


def _process(
    submission: praw.models.Submission,
    spotify: Client,
    threshold: float,
) -> Optional[Tuple[str, str]]:
    """Worker thread process for resolving a submission to a track.

    Args:
        submission: Reddit Submission object.
        spotify: Spotify API client.
        threshold: Minimum Levenshtein distance.

    Returns:
        Tuple of (track_id/url, title) or None.
    """
    # Direct Spotify links can be returned as-is
    if "spotify.com/track/" in submission.url:
        return (submission.url, submission.title)

    return _fuzzy_match(spotify, submission.title, threshold)


def _track_name_too_similar(
    track: str,
    playlist_track_names: set,
) -> bool:
    """Check if a track is too similar to existing tracks.

    Args:
        track: Track name to check.
        playlist_track_names: Set of existing track names.

    Returns:
        True if the track is a duplicate.
    """
    if is_duplicate_track(track, playlist_track_names, threshold=90.0):
        for other in playlist_track_names:
            from fuzzywuzzy import fuzz

            if fuzz.ratio(track.lower(), other.lower()) > 90:
                logger.warning(
                    f'Candidate new track "{track}" is too similar to '
                    f'existing track "{other}"'
                )
                return True
    return False


def _update_existing_playlist(
    spotify: Client,
    playlist_id: str,
    new_tracks: List[Tuple[str, str]],
    limit: Optional[int],
    verbosity: int,
) -> Dict[str, Any]:
    """Updates an existing playlist with new tracks (LIFO queue behavior).

    Args:
        spotify: Spotify client.
        playlist_id: Spotify playlist ID.
        new_tracks: List of (track_id, track_name) tuples.
        limit: Maximum number of tracks in playlist.
        verbosity: Verbosity level.

    Returns:
        Playlist object.
    """
    import sys

    if limit is None:
        limit = sys.maxsize  # pragma: no cover

    # Get current playlist and tracks
    playlist_object = spotify.playlist(playlist_id)
    _playlist = playlist_object
    tracks = _playlist["tracks"]["items"]

    # Paginate to get all tracks
    try:
        while _playlist["tracks"]["next"]:
            _playlist = spotify.next(_playlist["tracks"])
            try:
                tracks.extend(_playlist["tracks"]["items"])
            except KeyError:
                tracks.extend(_playlist["items"])
    except KeyError:
        tracks.extend(_playlist.get("items", []))
    except Exception as exc:
        logger.error(f"Failed to get tracks from playlist: {exc}")

    # Build sets of existing track IDs and names
    track_count = len(tracks)
    track_index = 0
    add_payload = []
    tracks_added = []
    remove_payload = []
    tracks_removed = []
    ids = set()
    playlist_track_names = set()

    for track in tracks:
        track_data = track["track"]
        ids.add(track_data["id"])
        artists = ", ".join([x["name"] for x in track_data["artists"]])
        playlist_track_names.add(f'{track_data["name"]} - {artists}')

    # Process new tracks
    for id_, track_name in new_tracks:
        # Resolve URL to track ID if needed
        if "spotify.com/track/" in id_:
            resp = spotify.track(id_)
            id_ = resp["id"]
            artists = ", ".join([x["name"] for x in resp["artists"]])
            track_name = f'{resp["name"]} - {artists}'

        if id_ in ids:
            logger.warning(
                f'Candidate new track "{track_name}" is already in the playlist'
            )
            continue

        if _track_name_too_similar(track_name, playlist_track_names):
            continue  # pragma: no cover

        tracks_added.append(track_name)
        add_payload.append(id_)

        # Remove oldest track if we'd exceed limit
        if track_count + len(tracks_added) > limit:
            _track = tracks.pop(0)["track"]
            artists = ", ".join([x["name"] for x in _track["artists"]])
            tracks_removed.append(f'{_track["name"]} - {artists}')
            remove_payload.append(
                {"uri": _track["uri"], "positions": [track_index]}
            )
            track_index += 1
            track_count -= 1

    # Log what we're doing
    if tracks_added:
        logger.info(f"{len(tracks_added)} new tracks added")
        if verbosity > 0:
            for track in tracks_added:
                logger.info(f"\t{track}")

    if tracks_removed:
        logger.info(f"{len(tracks_removed)} old tracks removed")
        if verbosity > 0:  # pragma: no cover
            for track in tracks_removed:
                logger.info(f"\t{track}")

    if not (tracks_added or tracks_removed):
        logger.info("No tracks added or removed")

    # Execute the changes
    if remove_payload:
        spotify.playlist_remove_specific_occurrences_of_items(
            playlist_id, remove_payload
        )
    if add_payload:
        spotify.playlist_add_items(playlist_id, add_payload)

    return playlist_object
