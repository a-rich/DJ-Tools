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
import shutil
from typing import Dict, List, Union
from urllib.parse import quote, unquote

import bs4
from bs4 import BeautifulSoup
from tqdm import tqdm

from .helpers import make_dirs


def copy_playlists_tracks(
    config: Dict[str, Union[List, Dict, str, bool, int, float]]
):
    """Copies tracks from provided playlists to a destination.

    Writes a new XML with these playlists and updated Location fields.

    Args:
        config: Configuration object.

    Raises:
        KeyError: "XML_PATH" must be set in "config.json".
        KeyError: "COPY_PLAYLISTS_TRACKS" and
            "COPY_PLAYLISTS_TRACKS_DESTINATION" must be set in "config.json".
        LookupError: Playlist names in COPY_PLAYLISTS_TRACKS must exist in
            "XML_PATH".
    """
    # Load Rekordbox dtabase from XML
    rekordbox_database_path = config.get("XML_PATH")
    if not rekordbox_database_path:
        raise KeyError(
            "Using the copy_playlists_tracks module requires the config option "
            "XML_PATH"
        ) from KeyError
    if not os.path.exists(rekordbox_database_path):
        raise FileNotFoundError(
            "Using the copy_playlists_tracks module requires the config option "
            "XML_PATH to be a valid rekordbox XML file"
        )
    with open(rekordbox_database_path, mode="r", encoding="utf-8") as _file:	
        rekordbox_database = BeautifulSoup(_file.read(), "xml")

    # Get playlists with tracks to be copied and destination to copy tracks to.
    playlists = config.get("COPY_PLAYLISTS_TRACKS")
    destination = config.get("COPY_PLAYLISTS_TRACKS_DESTINATION")
    if not playlists and destination:
        raise KeyError(
            "Using the copy_playlists_tracks module requires the config "
            "options COPY_PLAYLISTS_TRACKS and "
            "COPY_PLAYLISTS_TRACKS_DESTINATION"
        ) from KeyError

    # Create destination directory.
    make_dirs(destination)

    # Nodes to not remove when writing the new XML.
    keep_nodes = set()

    # Get the set of track IDs across the provided playlists.
    # Get the parents of playlists so they aren't removed from the output XML.
    playlists_track_keys = defaultdict(set)
    for playlist_name in playlists:
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
        [destination] * len(flattened_track_keys),
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
    for playlist_name in playlists:
        playlist = rekordbox_database.find_all(
            "NODE", {"Name": playlist_name}
        )[0]
        for track_id in playlists_track_keys[playlist_name]:
            playlist.append(rekordbox_database.new_tag("TRACK", Key=track_id))
    
    # Write new XML.
    new_rekordbox_database_path = os.path.join(
        os.path.dirname(rekordbox_database_path),
        f"relocated_{os.path.basename(rekordbox_database_path)}"
    ).replace(os.sep, "/")
    with open(
        new_rekordbox_database_path,
        mode="wb",
        encoding=rekordbox_database.original_encoding,
    ) as _file:
        _file.write(rekordbox_database.prettify("utf-8"))


def copy_file(
    track: bs4.element.Tag,
    destination: str,
    loc_prefix: str="file://localhost",
):
    """Copies tracks to a destination and writes new Location field.

    Args:
        track: TRACK node from XML.
        destination: Directory to copy tracks to.
        loc_prefix: Location field prefix.
    """
    loc = unquote(track["Location"]).split(loc_prefix)[-1]
    new_loc = os.path.join(
        destination, os.path.basename(loc)
    ).replace(os.sep, "/")
    shutil.copyfile(loc, new_loc)		
    track["Location"] = f"{loc_prefix}{quote(new_loc)}"
