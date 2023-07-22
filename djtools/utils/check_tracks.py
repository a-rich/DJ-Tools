"""This module is used to compare tracks from Spotify playlists and / or local
directories to see if there is any overlap with the contents of the Beatcloud.
"""
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
    download_spotify_playlist: Optional[str] = "",
) -> Tuple[List[str], List[str]]:
    """Compares tracks from Spotify / local with Beatcloud tracks.
    
    Gets track titles and artists from Spotify playlist(s) and / or file names
    from local directories, and get file names from the beatcloud. Then compute
    the Levenshtein similarity between their product in order to identify any
    overlapping tracks.

    Args:
        config: Configuration object.
        beatcloud_tracks: Cached list of tracks from S3.
        download_spotify_playlist: Override CHECK_TRACKS_SPOTIFY_PLAYLISTS and
            CHECK_TRACKS_LOCAL_DIRS and use this value instead.

    Returns:
        List of all tracks and list of full paths to matching Beatcloud tracks.
    """
    if download_spotify_playlist:
        cached_playlists = config.CHECK_TRACKS_SPOTIFY_PLAYLISTS
        cached_local_dirs = config.CHECK_TRACKS_LOCAL_DIRS
        config.CHECK_TRACKS_SPOTIFY_PLAYLISTS = [download_spotify_playlist]
        config.CHECK_TRACKS_LOCAL_DIRS = []

    track_sets = []
    beatcloud_matches = []
    if config.CHECK_TRACKS_SPOTIFY_PLAYLISTS:
        tracks = get_spotify_tracks(config)
        if not tracks:
            logger.warning(
                "There are no Spotify tracks; make sure "
                "CHECK_TRACKS_SPOTIFY_PLAYLISTS has one or more keys from "
                "spotify_playlists.yaml"
            )
        else:
            track_sets.append((tracks, "Spotify Playlist Tracks"))
    if config.CHECK_TRACKS_LOCAL_DIRS:
        tracks = get_local_tracks(config)
        if not tracks:
            logger.warning(
                "There are no local tracks; make sure CHECK_TRACKS_LOCAL_DIRS "
                'has one or more directories containing one or more tracks'
            )
        else:
            track_sets.append((tracks, "Local Directory Tracks"))

    if not track_sets:
        return beatcloud_tracks, beatcloud_matches

    if not beatcloud_tracks:
        beatcloud_tracks = get_beatcloud_tracks()

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

    if download_spotify_playlist:
        config.CHECK_TRACKS_SPOTIFY_PLAYLISTS = cached_playlists
        config.CHECK_TRACKS_LOCAL_DIRS = cached_local_dirs

    return beatcloud_tracks, beatcloud_matches
