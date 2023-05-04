"""This module is used to emulate shuffling the track order of one or more
playlists. This is done by setting the Rekordbox tag (i.e. "TrackNumber") of
tracks in the playlists to sequential numbers. After setting the TrackNumber
tags of tracks in the provided playlists, those tracks must be re-imported
for Rekordbox to be aware of the update.
"""
from concurrent.futures import ThreadPoolExecutor
import logging
import os
import random

from bs4 import BeautifulSoup
from tqdm import tqdm


from djtools.configs.config import BaseConfig
from djtools.rekordbox.helpers import get_playlist_tracks, set_track_number


logger = logging.getLogger(__name__)


def shuffle_playlists(config: BaseConfig):
    """For each playlist in "SHUFFLE_PLAYLISTS", shuffle the tracks and
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

    # Build a list of tracks to shuffle from the provided list of playlists.
    seen_tracks = set()
    shuffled_tracks = []
    for playlist in config.SHUFFLE_PLAYLISTS:
        try:
            tracks = get_playlist_tracks(soup, playlist, seen_tracks)
        except LookupError as exc:
            raise LookupError(f"{playlist} not found") from exc

        random.shuffle(tracks)
        shuffled_tracks.extend(tracks)

    # Shuffle the track number field of the tracks.
    shuffled_tracks = [lookup[x] for x in shuffled_tracks]
    payload = [shuffled_tracks, list(range(1, len(shuffled_tracks) + 1))]
    with ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as executor:
        _ = list(
            tqdm(
                executor.map(set_track_number, *payload),
                total=len(shuffled_tracks),
                desc=f"Randomizing {len(shuffled_tracks)} tracks",
            )
        )

    # Insert shuffled tracks playlist into the playlist root.
    playlists_root = soup.find_all("NODE", {"Name": "ROOT", "Type": "0"})[0]
    new_playlist = soup.new_tag(
        "NODE", KeyType="0", Name="AUTO_SHUFFLE", Type="1"
    )
    for track in shuffled_tracks:
        new_playlist.append(soup.new_tag("TRACK", Key=track["TrackID"]))
    playlists_root.insert(0, new_playlist)

    # Write XML file.
    _dir = config.XML_PATH.parent
    _file = config.XML_PATH.name
    auto_xml_path = _dir / f"auto_{_file}"
    with open(
        auto_xml_path, mode="wb", encoding=soup.orignal_encoding
    ) as _file:
        _file.write(soup.prettify("utf-8"))
