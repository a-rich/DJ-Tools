"""This module creates or updates Spotify playlists.

Playlists can be created from:
1. Discord webhook output from `djtools.sync.sync_operations.upload_music`
2. Subreddit posts (directly linked Spotify tracks or fuzzy-matched titles)
"""

import asyncio
import logging
from pathlib import Path
from typing import Type

import pyperclip
import yaml

from djtools.spotify.helpers import (
    filter_results,
    get_playlist_ids,
    get_reddit_client,
    get_spotify_client,
    get_subreddit_posts,
    populate_playlist,
    write_playlist_ids,
)


BaseConfig = Type["BaseConfig"]

# Silence PRAW, Spotify, and urllib3 loggers
for logger_name in ["asyncprawcore", "spotipy", "urllib3"]:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def async_spotify_playlists(config: BaseConfig):
    """Updates Spotify playlists from subreddit posts.

    Args:
        config: Configuration object.
    """
    spotify = get_spotify_client(config)
    reddit = get_reddit_client(config)
    playlist_ids = get_playlist_ids()

    # Load praw cache
    praw_cache = {}
    cache_file = Path(__file__).parent / ".praw.cache"
    if cache_file.exists():
        with open(cache_file, mode="r", encoding="utf-8") as _file:
            praw_cache = yaml.load(_file, Loader=yaml.FullLoader) or {}

    # Create async tasks for each subreddit
    tasks = [
        asyncio.create_task(
            get_subreddit_posts(spotify, reddit, subreddit, config, praw_cache)
        )
        for subreddit in config.spotify.spotify_playlist_subreddits
    ]

    # Process results as they complete
    for task in asyncio.as_completed(tasks):
        tracks, subreddit = await task
        playlist_ids = populate_playlist(
            playlist_name=subreddit.name,
            playlist_ids=playlist_ids,
            spotify_username=config.spotify.spotify_username,
            spotify=spotify,
            tracks=tracks,
            playlist_limit=subreddit.limit,
            verbosity=config.verbosity,
        )

    await reddit.close()

    # Save state
    write_playlist_ids(playlist_ids)
    with open(cache_file, mode="w", encoding="utf-8") as _file:
        yaml.dump(praw_cache, _file)


def spotify_playlist_from_upload(config: BaseConfig):
    """Generates a Spotify playlist from Discord webhook output.

    Uses clipboard contents containing upload_music webhook output to
    create a Spotify playlist of those tracks.

    Args:
        config: Configuration object.

    Raises:
        RuntimeError: If clipboard is empty.
    """
    data = pyperclip.paste()
    if not data:
        raise RuntimeError(
            "Generating a Spotify playlist from an upload requires output "
            "from an upload_music Discord webhook to be copied to the "
            "system's clipboard"
        )

    spotify = get_spotify_client(config)
    playlist_ids = get_playlist_ids()

    # Parse (track title, artist name) tuples from upload output
    user = ""
    files = []
    for line in data.split("\n"):
        if not line.startswith(" "):
            if not user:
                user = line.split("/")[0]
            continue
        file_ = Path(line).stem
        try:
            track, artist = file_.strip().split(" - ")
        except ValueError:
            logger.warning(f"{line.strip()} is not a valid file")
            continue
        if config.sync.artist_first:
            track, artist = artist, track
        files.append((track, artist))

    files = list(filter(lambda x: len(x) == 2, files))

    # Search Spotify for each file
    threshold = config.spotify.spotify_playlist_fuzz_ratio
    tracks = []
    for title, artist in files:
        query = f"track:{title} artist:{artist}"
        try:
            results = spotify.search(q=query, type="track", limit=50)
        except Exception as exc:
            logger.error(f'Error searching for "{title} - {artist}": {exc}')
            continue

        match, _ = filter_results(spotify, results, threshold, title, artist)
        if match:
            artists = ", ".join([y["name"] for y in match["artists"]])
            logger.info(
                f"Matched {match['name']} - {artists} to {title} - {artist}"
            )
        else:
            logger.warning(f"Could not find a match for {title} - {artist}")
            continue
        tracks.append((match["id"], f'{match["name"]} - {artists}'))

    # Populate playlist
    playlist_ids = populate_playlist(
        playlist_name=f"{user} Uploads",
        playlist_ids=playlist_ids,
        spotify_username=config.spotify.spotify_username,
        spotify=spotify,
        tracks=tracks,
        verbosity=config.verbosity,
    )

    write_playlist_ids(playlist_ids)


def spotify_playlists(config: BaseConfig):
    """Entry point for async Spotify playlist updates.

    Args:
        config: Configuration object.
    """
    asyncio.run(async_spotify_playlists(config))
