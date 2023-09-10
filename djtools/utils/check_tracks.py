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
        List of all tracks and list of full paths to matching Beatcloud tracks.
    """
    if config.DOWNLOAD_SPOTIFY_PLAYLIST:
        cached_local_dirs = config.LOCAL_DIRS
        config.LOCAL_DIRS = []

    track_sets = []
    beatcloud_matches = []
    spotify_playlists = (
        [config.DOWNLOAD_SPOTIFY_PLAYLIST]
        if config.DOWNLOAD_SPOTIFY_PLAYLIST
        else config.CHECK_TRACKS_SPOTIFY_PLAYLISTS
    )
    if spotify_playlists:
        tracks = get_spotify_tracks(config, spotify_playlists)
        if not tracks:
            if config.DOWNLOAD_SPOTIFY_PLAYLIST:
                substring = "DOWNLOAD_SPOTIFY_PLAYLIST is a key"
            else:
                substring = (
                    "CHECK_TRACKS_SPOTIFY_PLAYLISTS has one or more keys"
                )
            logger.warning(
                f"There are no Spotify tracks; make sure {substring} from "
                "spotify_playlists.yaml"
            )
        else:
            for playlist_name, playlist_tracks in tracks.items():
                track_title_artists = []
                for track in playlist_tracks:
                    title = track["track"]["name"]
                    artists = ", ".join([y["name"] for y in track["track"]["artists"]])
                    track_title_artists.append(
                        f"{artists} - {title}" if config.ARTIST_FIRST else f"{title} - {artists}"
                    )
                tracks[playlist_name] = track_title_artists
            track_sets.append((tracks, "Spotify Playlist Tracks"))
    if config.LOCAL_DIRS:
        tracks = get_local_tracks(config)
        if not tracks:
            logger.warning(
                "There are no local tracks; make sure LOCAL_DIRS has one or "
                "more directories containing one or more tracks"
            )
        else:
            tracks = {
                key: [track.stem for track in value]
                for key, value in tracks.items()
            }
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

    if config.DOWNLOAD_SPOTIFY_PLAYLIST:
        config.LOCAL_DIRS = cached_local_dirs

    return beatcloud_tracks, beatcloud_matches
