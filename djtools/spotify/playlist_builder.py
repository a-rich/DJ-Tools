"""This module is responsible for creating or updating Spotify playlists. This
can be done in a couple of ways.

The first way is by using the posted output from
`djtools.sync.sync_operations.upload_music`. When another user uploads music to
the Beatcloud, you may want to generate a Spotify playlist from those tracks so
they may be previewed before you decide whether or not to download them.

The second way is by querying subreddit posts. Posts are first checked to see
if they are direct links to a Spotify track. If this is not the case, then the
post title is parsed in an attempt to interpret it as either
'ARTIST NAME - TRACK TITLE' or 'TRACK TITLE - ARTIST NAME'. These components
are then used to search the Spotify API for tracks. The resulting tracks have
their title and artist fields compared with the reddit post title and are added
to the respective playlist if the Levenshtein similarity passes a threshold.
"""
import asyncio
import logging
from pathlib import Path

import pyperclip
import yaml

from djtools.configs.config import BaseConfig
from djtools.spotify.helpers import (
    filter_results,
    get_playlist_ids,
    get_reddit_client,
    get_spotify_client,
    get_subreddit_posts,
    populate_playlist,
    write_playlist_ids,
)


# Silence PRAW, Spotify, and urllib3 loggers.
for logger in ["asyncprawcore", "spotipy", "urllib3"]:
    logger = logging.getLogger(logger)
    logger.setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def async_spotify_playlists(config: BaseConfig):
    """This function updates the contents of one or more Spotify playlists with
        the posts of one or more subreddits (currently only supports one
        subreddit per playlist).

    Args:
        config: Configuration object.
    """
    spotify = get_spotify_client(config)
    reddit = get_reddit_client(config)
    playlist_ids = get_playlist_ids()

    praw_cache = {}
    cache_file = Path(__file__).parent / ".praw.cache"
    if cache_file.exists():
        with open(cache_file, mode="r", encoding="utf-8") as _file:
            praw_cache = yaml.load(_file, Loader=yaml.FullLoader) or {}

    tasks = [
        asyncio.create_task(
            get_subreddit_posts(
                spotify,
                reddit,
                subreddit,
                config,
                praw_cache,
            )
        )
        for subreddit in config.SPOTIFY_PLAYLIST_SUBREDDITS
    ]

    for task in asyncio.as_completed(tasks):
        tracks, subreddit = await task
        playlist_ids = populate_playlist(
            playlist_name=subreddit["name"],
            playlist_ids=playlist_ids,
            spotify_username=config.SPOTIFY_USERNAME,
            spotify=spotify,
            tracks=tracks,
            playlist_limit=subreddit["limit"],
            verbosity=config.VERBOSITY,
        )

    await reddit.close()

    write_playlist_ids(playlist_ids)

    with open(cache_file, mode="w", encoding="utf-8") as _file:
        yaml.dump(praw_cache, _file)


def spotify_playlist_from_upload(config: BaseConfig):
    """Generates a Spotify playlist using a Discord webhook output.

    If "upload_output", a path to a text file containing the pasted output of
    the upload_music Discord webhook output, is provided, this is used to
    generate a Spotify playlist of those uploaded tracks. If this is not
    provided, then the clipboard contents are used instead.

    Args:
        config: Configuration object.

    Raises:
        RuntimeError: Output from an upload_music Discord webhook must be
            copied to the system's clipboard
    """
    # Load upload output from the system's clipboard.
    data = pyperclip.paste()
    if not data:
        raise RuntimeError(
            "Generating a Spotify playlist from an upload requires output "
            "from an upload_music Discord webhook to be copied to the "
            "system's clipboard"
        )

    spotify = get_spotify_client(config)
    playlist_ids = get_playlist_ids()

    # Get (track title, artist name) tuples from file uploads.
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
            logger.warning(f'{line} is not a valid file')
            continue
        if config.ARTIST_FIRST:
            track, artist = artist, track
        files.append((track, artist))
    files = list(filter(lambda x: len(x) == 2, files))

    # Query Spotify for files in upload output.
    threshold = config.SPOTIFY_PLAYLIST_FUZZ_RATIO
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
            logger.info(f"Matched {match['name']} - {artists} to {title} - {artist}")
        else:
            logger.warning(f"Could not find a match for {title} - {artist}")
            continue
        tracks.append((match["id"], f'{match["name"]} - {artists}'))

    playlist_ids = populate_playlist(
        playlist_name=f"{user} Uploads",
        playlist_ids=playlist_ids,
        spotify_username=config.SPOTIFY_USERNAME,
        spotify=spotify,
        tracks=tracks,
        verbosity=config.VERBOSITY,
    )

    write_playlist_ids(playlist_ids)


def spotify_playlists(config: BaseConfig):
    """This function asynchronously updates Spotify playlists.

    Args:
        config: Configuration object.
    """
    asyncio.run(async_spotify_playlists(config))
