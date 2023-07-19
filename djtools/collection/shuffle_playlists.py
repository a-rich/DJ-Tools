"""This module is used to emulate shuffling the track order of one or more
playlists. This is done by setting the track number attribute of each track in
sequential order after collecting the set of Tracks from the provided
playlist(s).
"""
from concurrent.futures import as_completed, ThreadPoolExecutor
import logging
import os
import random

from tqdm import tqdm

from djtools.configs.config import BaseConfig
from djtools.collection.helpers import PLATFORM_REGISTRY


logger = logging.getLogger(__name__)


def shuffle_playlists(config: BaseConfig):
    """For each playlist in "SHUFFLE_PLAYLISTS", shuffle the tracks and
    sequentially set the track number to emulate shuffling.

    Args:
        config: Configuration object.
    """
    # Load collection.
    collection = PLATFORM_REGISTRY[config.PLATFORM]["collection"](
        path=config.COLLECTION_PATH
    )

    # Build a dict of tracks to shuffle from the provided list of playlists.
    shuffled_tracks = {}
    for playlist_name in config.SHUFFLE_PLAYLISTS:
        playlists = collection.get_playlists(playlist_name)
        if not playlists:
            raise LookupError(f"{playlist_name} not found")
        for playlist in playlists:
            tracks = playlist.get_tracks()
            track_keys = list(tracks.keys())
            random.shuffle(track_keys)
            shuffled_tracks.update({key: tracks[key] for key in track_keys})

    # Apply the shuffled track number to the attribute of the tracks.
    shuffled_tracks = list(shuffled_tracks.values())
    payload = [shuffled_tracks, list(range(1, len(shuffled_tracks) + 1))]
    with ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as executor:
        futures = [
            executor.submit(track.set_track_number, number)
            for track, number in zip(*payload)
        ]
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc=f"Randomizing {len(futures)} tracks",
        ):
            _ = future.result()

    # Reset the collection's playlists and insert a new playlist containing
    # just the shuffled tracks.
    collection.reset_playlists()
    collection.add_playlist(
        PLATFORM_REGISTRY[config.PLATFORM]["playlist"].new_playlist(
            name="SHUFFLE",
            tracks={track.get_id(): track for track in shuffled_tracks},
        )
    )
    _ = collection.serialize()
