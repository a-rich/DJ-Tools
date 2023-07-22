"""This module is used to copy the audio files from the provided playlists to a
new location and serialize a new collection with those tracks pointing to these
new locations.

The purpose of this utility is to:

* backup subsets of your library
* ensure you have easy access to a preparation independent of the setup
"""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import os

from tqdm import tqdm

from djtools.collection.helpers import copy_file, PLATFORM_REGISTRY
from djtools.configs.config import BaseConfig


def copy_playlists(config: BaseConfig):
    """Copies tracks from provided playlists to a destination.

    Serializes the collection with these playlists and updated locations.

    Args:
        config: Configuration object.

    Raises:
        LookupError: Playlist names in COPY_PLAYLISTS must exist in
            "COLLECTION_PATH".
    """
    # Load collection.
    collection = PLATFORM_REGISTRY[config.PLATFORM]["collection"](
        path=config.COLLECTION_PATH
    )

    # Create destination directory.
    config.COPY_PLAYLISTS_DESTINATION.mkdir(parents=True, exist_ok=True)

    playlist_tracks = {}
    lineage = defaultdict(set)
    playlists = []

    # Get the playlists from the collection.
    for playlist_name in config.COPY_PLAYLISTS:
        found_playlists = collection.get_playlists(playlist_name)
        if not found_playlists:
            raise LookupError(f"{playlist_name} not found")
        playlists.extend(
            [
                playlist for playlist in found_playlists
                if not playlist.is_folder()
            ]
        )

    # Traverse the playlist to get tracks for the desired playlists and mark
    # the rest for removal.
    for playlist in playlists:
        playlist_tracks.update(playlist.get_tracks())
        parent = playlist.get_parent()
        while parent:
            for child in list(parent):
                if child is not playlist and child not in lineage:
                    lineage[parent].add(child)
                    continue
                if any(child in children for children in lineage.values()):
                    lineage[parent].discard(child)
            parent = parent.get_parent()
    collection.set_tracks(playlist_tracks)

    # Remove the extra playlists.
    for parent, children in lineage.items():
        for child in children:
            parent.remove_playlist(child)

    # Copy tracks to the destination and update their location.
    payload = [
        playlist_tracks.values(),
        [config.COPY_PLAYLISTS_DESTINATION] * len(playlist_tracks),
    ]
    with ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as executor:
        _ = list(
            tqdm(
                executor.map(copy_file, *payload),
                total=len(playlist_tracks),
                desc=f"Copying {len(playlist_tracks)} tracks",
            )
        )

    # Serialize the new collection.
    _ = collection.serialize()
