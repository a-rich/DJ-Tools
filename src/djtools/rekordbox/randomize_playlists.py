"""This module is used to emulate shuffling the track order of one or more
playlists. This is done by setting the Rekordbox tag (i.e. "TrackNumber") of
tracks in the playlists to sequential numbers. After setting the TrackNumber
tags of tracks in the provided playlists, those tracks must be reimported
for Rekordbox to be aware of the update.
"""
from concurrent.futures import ThreadPoolExecutor
import logging
import os
import random

from bs4 import BeautifulSoup
from tqdm import tqdm


from djtools.configs.config import BaseConfig
from djtools.rekordbox.helpers import get_playlist_track_locations, set_tag


logger = logging.getLogger(__name__)


def randomize_playlists(config: BaseConfig):
    """For each playlist in "RANDOMIZE_PLAYLISTS", shuffle the tracks and
    sequentially set the TrackNumber tag to a number to emulate track
    randomization.

    Args:
        config: Configuration object.
    """
    # Load Rekordbox database from XML.
    with open(config.XML_PATH, mode="r", encoding="utf-8") as _file:
        soup = BeautifulSoup(_file.read(), "xml")

    # Create track ID lookup.
    lookup = {}
    for track in soup.find_all("TRACK"):
        if not track.get("Location"):
            continue
        lookup[track["TrackID"]] = track

    # Build a list of tracks to randomize from the provided list of playlists.
    seen_tracks = set()
    randomized_tracks = []
    for playlist in config.RANDOMIZE_PLAYLISTS:
        try:
            tracks = get_playlist_track_locations(soup, playlist, seen_tracks)
        except LookupError as exc:
            raise LookupError(f"{playlist} not found")

        random.shuffle(tracks)
        randomized_tracks.extend(tracks)

    # Shuffle the track number field of the tracks.
    randomized_tracks = [lookup[x] for x in randomized_tracks]
    payload = [randomized_tracks, list(range(1, len(randomized_tracks) + 1))]
    with ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as executor:
        _ = list(
            tqdm(
                executor.map(set_tag, *payload),
                total=len(randomized_tracks),
                desc=f"Randomizing {len(randomized_tracks)} tracks",
            )
        )

    # Insert randomized tracks playlist into the playlist root.
    playlists_root = soup.find_all("NODE", {"Name": "ROOT", "Type": "0"})[0]
    new_playlist = soup.new_tag(
        "NODE", KeyType="0", Name="AUTO_RANDOMIZE", Type="1"
    )
    for track in randomized_tracks:
        new_playlist.append(soup.new_tag("TRACK", Key=track["TrackID"]))
    playlists_root.insert(0, new_playlist)

    # Write XML file.
    _dir, _file = os.path.split(config.XML_PATH)
    auto_xml_path = os.path.join(_dir, f"auto_{_file}").replace(os.sep, "/")
    with open(
        auto_xml_path, mode="wb", encoding=soup.orignal_encoding
    ) as _file:
        _file.write(soup.prettify("utf-8"))
