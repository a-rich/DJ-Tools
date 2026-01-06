"""This module is used to copy the audio files from the provided playlists to a
new location and serialize a new collection with those tracks pointing to these
new locations.

The purpose of this utility is to:

* backup subsets of your library
* ensure you have easy access to a preparation independent of the setup
"""

# pylint: disable=duplicate-code
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Type

from tqdm import tqdm

from djtools.collection.helpers import copy_file
from djtools.collection.platform_registry import PLATFORM_REGISTRY
from djtools.utils.helpers import make_path

BaseConfig = Type["BaseConfig"]


@make_path
def copy_playlists(config: BaseConfig, path: Optional[Path] = None):
    """Copies tracks from provided playlists to a destination.

    Serializes the collection with these playlists and updated locations.

    Args:
        config: Configuration object.
        path: Path to write the new collection to.

    Raises:
        LookupError: Playlist names in copy_playlists must exist in
            "collection_path".
    """
    # Load collection.
    collection = PLATFORM_REGISTRY[config.collection.platform]["collection"](
        path=config.collection.collection_path
    )

    # Create destination directory.
    config.collection.copy_playlists_destination.mkdir(
        parents=True, exist_ok=True
    )

    playlist_tracks = {}
    lineage = defaultdict(set)
    playlists = []

    # Get the playlists from the collection.
    for playlist_name in config.collection.copy_playlists:
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
        [config.collection.copy_playlists_destination] * len(playlist_tracks),
        strict=True,
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
            config.collection.copy_playlists_destination
            / f"copied_playlists_collection{config.collection.collection_path.suffix}"
        )

    # Serialize the new collection.
    _ = collection.serialize(path=path)
