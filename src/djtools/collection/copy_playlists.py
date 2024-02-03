"""This module is used to copy the audio files from the provided playlists to a
new location and serialize a new collection with those tracks pointing to these
new locations.

The purpose of this utility is to:

* backup subsets of your library
* ensure you have easy access to a preparation independent of the setup
"""

# pylint: disable=duplicate-code
from collections import defaultdict
from concurrent.futures import as_completed, ThreadPoolExecutor
import os
from pathlib import Path
from typing import Optional

from tqdm import tqdm

from djtools.collection.helpers import copy_file, PLATFORM_REGISTRY
from djtools.configs.config import BaseConfig
from djtools.utils.helpers import make_path


@make_path
def copy_playlists(config: BaseConfig, path: Optional[Path] = None):
    """Copies tracks from provided playlists to a destination.

    Serializes the collection with these playlists and updated locations.

    Args:
        config: Configuration object.
        path: Path to write the new collection to.

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
                playlist
                for playlist in found_playlists
                if not playlist.is_folder()
            ]
        )

    # Traverse the playlist to get tracks for the desired playlists and mark
    # the rest for removal.
    for playlist in playlists:
        playlist_tracks.update(playlist.get_tracks())
        parent = playlist.get_parent()
        while parent:
            lineage[parent] = set()
            for child in list(parent):
                if child not in playlists and child not in lineage:
                    lineage[parent].add(child)
                    continue
            parent = parent.get_parent()
    collection.set_tracks(playlist_tracks)

    # Remove the extra playlists.
    for parent, children in lineage.items():
        for child in children:
            parent.remove_playlist(child)

    # Copy tracks to the destination and update their location.
    payload = zip(
        playlist_tracks.values(),
        [config.COPY_PLAYLISTS_DESTINATION] * len(playlist_tracks),
    )

    with ThreadPoolExecutor(
        max_workers=os.cpu_count() * 4  # pylint: disable=no-member
    ) as executor:
        futures = [executor.submit(copy_file, *args) for args in payload]

        with tqdm(total=len(futures), desc="Copying tracks") as pbar:
            for future in as_completed(futures):
                _ = future.result()
                pbar.update(1)

    # Unless specified, write the output collection to the same directory that
    # the files are being copied to.
    if not path:
        path = (
            config.COPY_PLAYLISTS_DESTINATION
            / f"copied_playlists_collection{config.COLLECTION_PATH.suffix}"
        )

    # Serialize the new collection.
    _ = collection.serialize(path=path)
