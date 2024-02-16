"""This module is used to compare tracks from Spotify playlists and / or local
directories to see if there is any overlap with the contents of the Beatcloud.
"""

from collections import defaultdict
from itertools import groupby
import logging
from operator import itemgetter
from typing import List, Optional, Tuple

from djtools.configs.config import BaseConfig
from djtools.utils.helpers import (
    find_matches,
    get_spotify_tracks,
    get_beatcloud_tracks,
    get_local_tracks,
    reverse_title_and_artist,
)


logger = logging.getLogger(__name__)


def compare_tracks(
    config: BaseConfig,
    beatcloud_tracks: Optional[List[str]] = None,
) -> Tuple[List[str], List[str]]:
    """Compares tracks from Spotify / local with Beatcloud tracks.

    Gets track titles and artists from Spotify playlist(s) and / or file names
    from local directories, and get file names from the beatcloud. Then compute
    the Levenshtein similarity between their product in order to identify any
    overlapping tracks.

    Args:
        config: Configuration object.
        beatcloud_tracks: Cached list of tracks from S3.

    Returns:
        Tuple with a list of all Beatcloud tracks and list of full paths to
            matching Beatcloud tracks.
    """
    if config.DOWNLOAD_SPOTIFY_PLAYLIST:
        cached_local_dirs = config.LOCAL_DIRS
        config.LOCAL_DIRS = []
        spotify_playlists = [config.DOWNLOAD_SPOTIFY_PLAYLIST]
    else:
        spotify_playlists = config.CHECK_TRACKS_SPOTIFY_PLAYLISTS

    track_sets = []
    beatcloud_matches = []
    if spotify_playlists:
        spotify_tracks = get_spotify_tracks(config, spotify_playlists)
        if not spotify_tracks:
            if config.DOWNLOAD_SPOTIFY_PLAYLIST:
                substring = "DOWNLOAD_SPOTIFY_PLAYLIST is a key"
            else:
                substring = (
                    "CHECK_TRACKS_SPOTIFY_PLAYLISTS has one or more keys"
                )
            logger.warning(
                f"There are no Spotify tracks; make sure {substring} in "
                "spotify_playlists.yaml"
            )
        else:
            track_results = defaultdict(list)
            for playlist_name, playlist_tracks in spotify_tracks.items():
                for track in playlist_tracks:
                    title = track["track"]["name"]
                    artists = ", ".join(
                        [y["name"] for y in track["track"]["artists"]]
                    )
                    track_results[playlist_name].append(
                        f"{artists} - {title}"
                        if config.ARTIST_FIRST
                        else f"{title} - {artists}"
                    )
            track_sets.append((track_results, "Spotify Playlist Tracks"))
    if config.LOCAL_DIRS:
        local_tracks = get_local_tracks(config)
        if not local_tracks:
            logger.warning(
                "There are no local tracks; make sure LOCAL_DIRS has one or "
                "more directories containing one or more tracks"
            )
        else:
            track_results = {
                key: [track.stem for track in value]
                for key, value in local_tracks.items()
            }
            track_sets.append((track_results, "Local Directory Tracks"))

    if config.DOWNLOAD_SPOTIFY_PLAYLIST:
        config.LOCAL_DIRS = cached_local_dirs

    if not track_sets:
        return beatcloud_tracks, beatcloud_matches

    if not beatcloud_tracks:
        beatcloud_tracks = get_beatcloud_tracks(config.BUCKET_URL)

    path_lookup = {x.stem: x for x in beatcloud_tracks}

    for tracks, track_type in track_sets:
        if config.ARTIST_FIRST and track_type == "Local Directory Tracks":
            path_lookup = reverse_title_and_artist(path_lookup)
        matches = find_matches(
            tracks,
            path_lookup.keys(),
            config,
        )
        logger.info(f"\n{track_type} / Beatcloud Matches: {len(matches)}")
        for loc, matches in groupby(
            sorted(matches, key=itemgetter(0)), key=itemgetter(0)
        ):
            logger.info(f"{loc}:")
            for _, track, beatcloud_track, fuzz_ratio in matches:
                beatcloud_matches.append(path_lookup[beatcloud_track])
                logger.info(f"\t{fuzz_ratio}: {track} | {beatcloud_track}")

    return beatcloud_tracks, beatcloud_matches
