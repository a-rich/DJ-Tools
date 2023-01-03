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
import json
import logging
import os
from typing import Dict, List, Union

import pyperclip

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


async def async_update_auto_playlists(
    config: Dict[str, Union[List, Dict, str, bool, int, float]]
):
    """This function updates the contents of one or more Spotify playlists with
        the posts of one or more subreddits (currently only supports one
        subreddit per playlist).

    Args:
        config: Configuration object.
    
    Raises:
        KeyError: "SPOTIFY_USERNAME" must be configured.
    """
    if not config.get("AUTO_PLAYLIST_SUBREDDITS"):
        logger.error(
            "Using the spotify.playlist_builder module requires the config "
            "option AUTO_PLAYLIST_SUBREDDITS"
        )
        return

    spotify = get_spotify_client(config)
    reddit = get_reddit_client(config)
    playlist_ids = get_playlist_ids()
    
    praw_cache = {}
    cache_file = os.path.join(
        os.path.dirname(__file__), ".praw.cache"
    ).replace(os.sep, "/")
    if os.path.exists(cache_file):
        with open(cache_file, mode="r", encoding="utf-8") as _file:
            praw_cache = json.load(_file)
    
    try:
        username = config["SPOTIFY_USERNAME"]
    except KeyError:
        raise KeyError(
            "The spotify.playlist_builder module requires the config option "
            "SPOTIFY_USERNAME"
        ) from KeyError

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
        for subreddit in config["AUTO_PLAYLIST_SUBREDDITS"]
    ]

    for task in asyncio.as_completed(tasks):
        tracks, subreddit = await task
        playlist_ids = populate_playlist(
            playlist_name=subreddit["name"],
            playlist_ids=playlist_ids,
            spotify_username=username,
            spotify=spotify,
            tracks=tracks,
            playlist_limit=subreddit["limit"],
            verbosity=config.get("VERBOSITY", 0),
        )
    
    await reddit.close()

    write_playlist_ids(playlist_ids)

    with open(cache_file, mode="w", encoding="utf-8") as _file:
        json.dump(praw_cache, _file)


def playlist_from_upload(
    config: Dict[str, Union[List, Dict, str, bool, int, float]],
):
    """Generates a Spotify playlist using a Discord webhook output.

    If "upload_output", a path to a text file containing the pasted output of
    the upload_music Discord webhook output, is provided, this is used to
    generate a Spotify playlist of those uploaded tracks. If this is not
    provided, then the clipboard contents are used instead.

    Args:
        config: Configuration object.

    Raises:
        KeyError: "PLAYLIST_FROM_UPLOAD" must be configured.
        FileNotFoundError: If "upload_output" is provided as a text file, that
            file must exist.
        RuntimeError: If not providing "upload_output" as a text file, it must
            be provided as system clipboard data.
        ValueError: "PLAYLIST_FROM_UPLOAD" must be either a file or boolean.
        KeyError: "SPOTIFY_USERNAME" must be provided to buld a new playlist.
    """
    try:
        upload_output = config["PLAYLIST_FROM_UPLOAD"]
    except KeyError:
        raise KeyError(
            "Using the playlist_from_upload function of the "
            "spotify.playlist_builder module requires the "
            "PLAYLIST_FROM_UPLOAD config option"
        ) from KeyError 

    # Load upload output from a text file.
    if isinstance(upload_output, str):
        if not os.path.exists(upload_output):
            raise FileNotFoundError(f"{upload_output} does not exit")
        with open(upload_output, mode="r", encoding="utf-8") as _file:
            data = _file.read()
    # Load upload output from the system's clipboard.
    elif isinstance(upload_output, bool):
        data = pyperclip.paste()
        if not data:
            raise RuntimeError(
                "Generating a Spotify playlist from an upload requires either "
                '"upload_output", a path to the upload_music Discord webhook '
                "output, or that output to be copied to the system's clipboard"
            )
    else:
        raise ValueError(
            "Config option PLAYLIST_FROM_UPLOAD must be either a path to a "
            f'file or a boolean, but got "{upload_output}"'
        )

    try:
        username = config["SPOTIFY_USERNAME"]
    except KeyError:
        raise KeyError(
            "The spotify.playlist_builder module requires the config option "
            "SPOTIFY_USERNAME"
        ) from KeyError

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
        file_, _ = os.path.splitext(line)
        try:
            track, artist = file_.strip().split(" - ")
        except ValueError:
            logger.warning(f'{line} is not a valid file')
            continue
        files.append((track, artist))
    files = list(filter(lambda x: len(x) == 2, files))

    # Query Spotify for files in upload output.
    threshold = config.get("CHECK_TRACK_OVERLAP_FUZZ_RATIO", 50)
    tracks = []
    for title, artist in files:
        artist = ", ".join(sorted([x.strip() for x in artist.split(",")]))
        query = (
            f'{title.replace(" ", "+")}+'
            f'{artist.replace(" ", "+").replace(",", "")}'
        )
        try:
            results = spotify.search(q=query, type="track", limit=50)
        except Exception as exc:
            logger.error(f'Error searching for "{title} - {artist}": {exc}')
            continue

        match = filter_results(spotify, results, threshold, title, artist)
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
        spotify_username=username,
        spotify=spotify,
        tracks=tracks,
        verbosity=config.get("VERBOSITY", 0),
    )

    write_playlist_ids(playlist_ids)


def update_auto_playlists(
    config: Dict[str, Union[List, Dict, str, bool, int, float]]
):
    """This function asynchronously updates Spotify playlists.

    Args:
        config: Configuration object.
    """
    asyncio.run(async_update_auto_playlists(config))
