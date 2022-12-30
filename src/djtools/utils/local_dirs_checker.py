"""This module is responsible foor identifying any potential overlap between
tracks in one or more local directory with all the tracks already in the
beatcloud.
"""
from glob import glob
from itertools import groupby
import logging
from operator import itemgetter
import os
from typing import Dict, List, Optional, Union

from djtools.spotify.spotify_playlist_checker import get_beatcloud_tracks, find_matches

logger = logging.getLogger(__name__)


def check_local_dirs(
    config: Dict[str, Union[List, Dict, str, bool, int, float]],
    beatcloud_tracks: Optional[List[str]] = [],
) -> List[str]:
    """Gets track titles and artists from both local files and beatcloud and 
        computes the Levenshtein similarity between their product in order to
        identify any overlapping tracks.

    Args:
        config: Configuration object.
        beatcloud_tracks: Cached response from listing Beatcloud contents.
    """
    local_tracks = get_local_tracks(config)
    if not local_tracks:
        logger.warning(
            "There are no local tracks; make sure LOCAL_CHECK_DIRS has one or "
            'more directories (under "DJ Music") containing one or more tracks'
        )
        return
    if not beatcloud_tracks:
        beatcloud_tracks = get_beatcloud_tracks()
    matches = find_matches(local_tracks, beatcloud_tracks, config)
    logger.info(f"Local tracks / beatcloud matches: {len(matches)}")
    for playlist, matches in groupby(
        sorted(matches, key=itemgetter(0)), key=itemgetter(0)
    ):
        logger.info(f"{playlist}:")
        for _, spotify_track, beatcloud_track, fuzz_ratio in matches:
            logger.info(f"\t{fuzz_ratio}: {spotify_track} | {beatcloud_track}")
    
    return beatcloud_tracks


def get_local_tracks(
    config: Dict[str, Union[List, Dict, str, bool, int, float]],
) -> List[str]:
    """Aggregates the files from one or more local directories in a dictionary
        mapped with parent directories.

    Args:
        config: Configuration object.

    Raises:
        KeyError: "LOCAL_CHECK_DIRS" must be configured.
        ValueError: "LOCAL_CHECK_DIRS" must be configured.

    Returns:
        Local file names keyed by parent directory.
    """
    if "LOCAL_CHECK_DIRS" not in config:
        raise KeyError(
            "Using the local_dirs_checker module requires the config option "
            "LOCAL_CHECK_DIRS to be set to a list of one or more directories "
            "containing new tracks"
        )
    if not config["LOCAL_CHECK_DIRS"]:
        raise ValueError(
            "Using the local_dirs_checker module requires the config option "
            "LOCAL_CHECK_DIRS to be set to a list of one or more directories "
            "containing new tracks"
        )

    local_dir_tracks = {}
    for _dir in config["LOCAL_CHECK_DIRS"]:
        path = _dir.replace(os.sep, "/")
        if not os.path.exists(path):
            logger.warning(
                f"{path} does not exist; will not be able to check its "
                "contents against the beatcloud"
            )
            continue
        files = glob(
            os.path.join(path, "**", "*.*").replace(os.sep, "/"),
            recursive=True,
        )
        if not files:
            continue
        local_dir_tracks[_dir] = [
            os.path.splitext(os.path.basename(x))[0] for x in files
        ]

    return local_dir_tracks
