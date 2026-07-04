"""This module contains helper functions used by the spotify module.

All Spotify API interactions are delegated to the spotify-tools library.
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
    PlaylistTrack,
    SpotifyConfig,
    create_playlist,
    get_playlist,
    resolve_track_from_url,
    search_track_fuzzy,
    update_playlist,
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
        spotify_config = config.spotify
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


async def get_subreddit_posts(
    spotify: Client,
    reddit: praw.Reddit,
    subreddit: SubredditConfig,
    config: BaseConfig,
    praw_cache: Dict[str, bool],
) -> Tuple[List[Tuple[str, str]], Dict[str, Union[str, int]]]:
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
    from concurrent.futures import ThreadPoolExecutor, as_completed

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

    new_tracks: List[Tuple[str, str]] = []
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
            strict=True,
        )

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(_process, *args) for args in payload]

            with tqdm(total=len(futures), desc=msg) as pbar:
                new_tracks = []
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        new_tracks.append(result)
                    pbar.update(1)

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
    tracks: List[Tuple[str, str]],
    playlist_limit: Optional[int] = None,
    verbosity: int = 0,
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

    # Convert track tuples to PlaylistTrack objects, resolving URLs if needed
    playlist_tracks = _resolve_tracks(spotify, tracks)

    if playlist_id and playlist_tracks:
        # Update existing playlist using spotify-tools
        result = update_playlist(
            spotify,
            playlist_id,
            playlist_tracks,
            max_size=playlist_limit,
            check_duplicates=True,
            duplicate_threshold=90.0,
            verbosity=verbosity,
        )
        _log_update_result(result, verbosity)
        playlist = get_playlist(spotify, playlist_id)
    elif playlist_tracks:
        # Create new playlist using spotify-tools
        logger.warning(
            f"Unable to get ID for {playlist_name}...creating a new playlist"
        )
        playlist = create_playlist(
            spotify,
            name=playlist_name.title(),
            tracks=playlist_tracks,
            public=True,
            user_id=spotify_username,
        )
        if playlist and playlist.id:
            playlist_ids[playlist_name] = playlist.id
    elif playlist_id:
        playlist = get_playlist(spotify, playlist_id)
    else:
        playlist = None

    if playlist:
        url = ""
        if playlist.external_urls:
            url = playlist.external_urls.spotify or ""
        logger.info(f'"{playlist.name}": {url}')

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


def filter_results(
    spotify: Client,
    results: Dict,
    threshold: float,
    title: str,
    artist: str,
) -> Tuple[Dict[str, Any], float]:
    """Filter Spotify search results to find best matching track.

    This function uses spotify-tools' search_track_fuzzy for matching.

    Args:
        spotify: Spotify client.
        results: Spotify search results (unused, kept for API compatibility).
        threshold: Minimum Levenshtein distance.
        title: Potential title of a track.
        artist: Potential artist of a track.

    Returns:
        Tuple of track object (as dict) and similarity score.
    """
    # Use spotify-tools search with pagination for thorough matching
    result = search_track_fuzzy(
        spotify, title, artist, threshold=threshold, limit=50
    )

    if result and result.track:
        return result.track.model_dump(), result.score

    return {}, 0.0


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


def _log_update_result(result, verbosity: int):
    """Log the result of a playlist update operation.

    Args:
        result: UpdateResult from spotify-tools.
        verbosity: Logging verbosity level.
    """
    if result.tracks_added:
        logger.info(f"{len(result.tracks_added)} new tracks added")
        if verbosity > 0:  # pragma: no cover
            for track in result.tracks_added:
                logger.info(f"\t{track.display_name}")

    if result.tracks_removed:
        logger.info(f"{len(result.tracks_removed)} old tracks removed")
        if verbosity > 0:  # pragma: no cover
            for track in result.tracks_removed:
                logger.info(f"\t{track.display_name}")

    if result.skipped_existing:
        for track in result.skipped_existing:
            logger.warning(
                f'Candidate new track "{track.display_name}" is already in '
                "the playlist"
            )

    if result.skipped_duplicates:
        for track in result.skipped_duplicates:
            logger.warning(
                f'Candidate new track "{track.display_name}" is too similar '
                "to existing track"
            )

    if not (result.tracks_added or result.tracks_removed):
        logger.info("No tracks added or removed")


def _parse_title(title: str) -> List[Optional[str]]:
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

    # Parse title into track/artist
    parts = _parse_title(submission.title)
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


def _resolve_tracks(
    spotify: Client,
    tracks: List[Tuple[str, str]],
) -> List[PlaylistTrack]:
    """Convert track tuples to PlaylistTrack objects.

    Resolves Spotify URLs to track IDs as needed.

    Args:
        spotify: Spotify client.
        tracks: List of (track_id_or_url, track_name) tuples.

    Returns:
        List of PlaylistTrack objects.
    """
    playlist_tracks = []
    for id_or_url, name in tracks:
        if "spotify.com/track/" in id_or_url:
            # Resolve URL to PlaylistTrack
            pt = resolve_track_from_url(spotify, id_or_url)
            if pt:
                playlist_tracks.append(pt)
        else:
            # Create PlaylistTrack from ID and name
            playlist_tracks.append(
                PlaylistTrack(
                    id=id_or_url,
                    uri=f"spotify:track:{id_or_url}",
                    name=name.split(" - ")[0] if " - " in name else name,
                    artists=name.split(" - ")[1] if " - " in name else "",
                )
            )
    return playlist_tracks
