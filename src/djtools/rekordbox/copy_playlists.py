"""This module is used to copy the audio files from the provided playlists to a
new location and write a new XML database with those tracks pointing to these
new locations.

The purpose of this utility is to:
    * backup subsets of your library
    * ensure you have easy access to a preparation on non-Pioneer setups
"""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import os

from bs4 import BeautifulSoup
from tqdm import tqdm

from djtools.configs.config import BaseConfig
from djtools.rekordbox.helpers import copy_file
from djtools.utils.helpers import make_dirs


def copy_playlists(config: BaseConfig):
    """Copies tracks from provided playlists to a destination.

    Writes a new XML with these playlists and updated Location fields.

    Args:
        config: Configuration object.

    Raises:
        LookupError: Playlist names in COPY_PLAYLISTS must exist in
            "XML_PATH".
    """
    # Load Rekordbox database from XML.
    with open(config.XML_PATH, mode="r", encoding="utf-8") as _file:	
        rekordbox_database = BeautifulSoup(_file.read(), "xml")

    # Create destination directory.
    make_dirs(config.COPY_PLAYLISTS_DESTINATION)

    # Nodes to not remove when writing the new XML.
    keep_nodes = set()

    # Get the set of track IDs across the provided playlists.
    # Get the parents of playlists so they aren't removed from the output XML.
    playlists_track_keys = defaultdict(set)
    for playlist_name in config.COPY_PLAYLISTS:
        try:
            playlist = rekordbox_database.find_all(
                "NODE", {"Name": playlist_name}
            )[0]
            keep_nodes.update([playlist_name])
            next_playlist = playlist
            while next_playlist.parent:
                next_playlist = next_playlist.parent
                if not next_playlist.attrs:
                    break
                keep_nodes.add(next_playlist.attrs["Name"])
        except IndexError:
            raise LookupError(f"{playlist_name} not found")
        playlists_track_keys[playlist_name].update(
            {track["Key"] for track in playlist.children if str(track).strip()}
        )
    flattened_track_keys = {
        track_key for track_keys in playlists_track_keys.values()
        for track_key in track_keys
    }

    # Get the map of track IDs to their TRACK nodes.
    # Decompose tracks that aren't in the provided playlists.
    tracks = {}
    for track in rekordbox_database.find_all("TRACK"):
        if (
            not track.get("Location")
            or track["TrackID"] not in flattened_track_keys 
        ):
            track.decompose()
        else:
            tracks[track["TrackID"]] = track

    # Copy tracks to the destination and update Location for the track.
    payload = [
        {tracks[key] for key in flattened_track_keys},
        [config.COPY_PLAYLISTS_DESTINATION] * len(flattened_track_keys),
    ]
    with ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as executor:
        _ = list(
            tqdm(
                executor.map(copy_file, *payload),
                total=len(flattened_track_keys),
                desc=f"Copying {len(flattened_track_keys)} tracks",
            )
        )

    # Decompose irrelevant playlists.
    playlists_root = rekordbox_database.find_all(
        "NODE", {"Name": "ROOT", "Type": "0"}
    )[0]
    for node in playlists_root.find_all("NODE"):
        if node.attrs and node.attrs["Name"] not in keep_nodes:
            node.decompose()
    
    # Repopulate playlists with relocated tracks.
    for playlist_name in config.COPY_PLAYLISTS:
        playlist = rekordbox_database.find_all(
            "NODE", {"Name": playlist_name}
        )[0]
        for track_id in playlists_track_keys[playlist_name]:
            playlist.append(rekordbox_database.new_tag("TRACK", Key=track_id))
    
    # Write new XML.
    new_rekordbox_database_path = os.path.join(
        os.path.dirname(config.XML_PATH),
        f"relocated_{os.path.basename(config.XML_PATH)}"
    ).replace(os.sep, "/")
    with open(
        new_rekordbox_database_path,
        mode="wb",
        encoding=rekordbox_database.original_encoding,
    ) as _file:
        _file.write(rekordbox_database.prettify("utf-8"))
