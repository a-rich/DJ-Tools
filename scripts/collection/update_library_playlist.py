"""This script is used to populate a Spotify playlist with tracks added to a
collection.
"""

# pylint: disable=missing-function-docstring,inconsistent-return-statements,protected-access,redefined-outer-name,R0801
import logging
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path
from typing import Union

from spotipy import Spotify
from tqdm import tqdm

from djtools.configs.config import BaseConfig
from djtools.collection import RekordboxCollection
from djtools.collection.base_track import Track
from djtools.configs import build_config
from djtools.spotify.helpers import (
    get_spotify_client,
    get_playlist_ids,
    filter_results,
    populate_playlist,
    write_playlist_ids,
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)
REQ_ID_LIMIT = 1


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("--config")
    parser.add_argument(
        "--date-filter",
        type=convert_to_datetime,
        default="most-recent",
        help=(
            "Datetime to after which tracks should have tags added from "
            "Spotify. Default is 'most-recent'."
        ),
    )
    parser.add_argument("--playlist-name", default="Library Tracks")
    args = parser.parse_args()

    return args


def convert_to_datetime(arg: str) -> Union[datetime, str]:
    """Convert string to datetime.

    Args:
        arg: datetime as a YYYY-MM-DD string

    Returns:
        Either the datetime object to filter after or a string indicating that
            the most recent upload should be filtered.
    """
    if arg in ["most-recent", "all"]:
        return arg

    try:
        return datetime.strptime(arg, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(
            f"Couldn't convert --date-filter argument '{arg}' into a datetime."
        ) from exc


def filter_tracks(
    tracks: dict[str, Track], date_filter: Union[datetime, str]
) -> dict[str, Track]:
    """Filter tracks using a date filter.

    Args:
        tracks: Dictionary of tracks to filter.
        date_filter: datetime to filter tracks with.

    Returns:
        Dictionary of filtered tracks.
    """
    if date_filter == "all":
        return tracks

    sorted_tracks = sorted(
        tracks.values(), key=lambda x: x.get_date_added(), reverse=True
    )

    if date_filter == "most-recent":
        date_filter = sorted_tracks[0].get_date_added()

    filtered_tracks = []
    for track in sorted_tracks:
        if track.get_date_added() < date_filter:
            break
        filtered_tracks.append(track)

    return {track.get_id(): track for track in filtered_tracks}


def find_track(track: Track, config: BaseConfig, spotify: Spotify):
    title = track._Name
    artist = track.get_artists()
    threshold = config.spotify.spotify_playlist_fuzz_ratio
    query = f"track:{title} artist:{artist}"
    try:
        results = spotify.search(q=query, type="track", limit=50)
    except Exception as exc:
        logger.error(f'Error searching for "{title} - {artist}": {exc}')
        return

    match, _ = filter_results(spotify, results, threshold, title, artist)
    if match:
        artists = ", ".join([y["name"] for y in match["artists"]])
        logger.warning(
            f"Matched {match['name']} - {artists} to {title} - {artist}"
        )
    else:
        logger.warning(f"Could not find a match for {title} - {artist}")
        return

    return (match["id"], f'{match["name"]} - {artists}')


def main(config_path: Path, date_filter: datetime, playlist_name: str):
    config = build_config(config_path)
    spotify = get_spotify_client(config)
    playlist_ids = get_playlist_ids()

    collection = RekordboxCollection(config.collection.collection_path)
    tracks = filter_tracks(collection.get_tracks(), date_filter)
    tracks = sorted(tracks.values(), key=lambda x: x.get_date_added())

    found_tracks = list(
        filter(
            None,
            [
                find_track(track, config, spotify)
                for track in tqdm(tracks, desc="Searching Spotify")
            ],
        )
    )

    num_chunks = len(found_tracks) // REQ_ID_LIMIT
    num_chunks += 0 if len(found_tracks) / REQ_ID_LIMIT == 0 else 1
    for index in tqdm(
        range(0, len(found_tracks), REQ_ID_LIMIT), total=num_chunks
    ):
        chunk = found_tracks[index : index + REQ_ID_LIMIT]
        playlist_ids = populate_playlist(
            playlist_name=playlist_name,
            playlist_ids=playlist_ids,
            spotify_username=config.spotify.spotify_username,
            spotify=spotify,
            tracks=chunk,
            verbosity=config.verbosity,
        )

        write_playlist_ids(playlist_ids)


if __name__ == "__main__":
    args = parse_args()
    main(
        args.config,
        args.date_filter,
        args.playlist_name,
    )
