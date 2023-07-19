"""This module contains helper functions that are not specific to any
particular sub-package of this library.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from itertools import product
import logging
import logging.config
import os
from pathlib import Path
from subprocess import check_output
import tempfile
from typing import Any, Dict, IO, List, Optional, Set, Tuple
from unittest import mock

from fuzzywuzzy import fuzz
import spotipy
from tqdm import tqdm

from djtools.configs.config import BaseConfig
from djtools.spotify.helpers import get_playlist_ids, get_spotify_client


logger = logging.getLogger(__name__)


class MockOpen:
    """Class for mocking the builtin open function."""
    builtin_open = open

    def __init__(
        self,
        files: List[str],
        user_a: Optional[Tuple[str]] = None,
        user_b: Optional[Tuple[str]] = None,
        content: Optional[str] = "",
        write_only: Optional[bool] = False,
    ):
        self._user_a = user_a
        self._user_b = user_b
        self._files = files
        self._content = content
        self._write_only = write_only

    def open(self, *args, **kwargs) -> IO:
        """Function to replace the builtin open function.

        Returns:
            File handler.
        """
        file_name = Path(args[0]).name
        if file_name in self._files:
            if "w" in kwargs.get("mode"):
                return tempfile.TemporaryFile(mode=kwargs["mode"])
            if not self._write_only:
                return self._file_strategy(file_name, *args, **kwargs)
        return self.builtin_open(*args, **kwargs)

    def _file_strategy(self, *args, **kwargs):
        """Apply logic for file contents based on file name.

        Returns:
            Mock file handler object.
        """
        data = "{}"
        if self._content:
            data = self._content

        return mock.mock_open(read_data=data)(*args, **kwargs)


def add_tracks(result: Dict[str, Any], artist_first: bool) -> List[str]:
    """Parses a page of Spotify API result tracks and returns a list of the
        track titles and artist names.

    Args:
        result: Paged result of Spotify tracks.
        artist_first: Whether or not artist should come before track title.

    Returns:
        Spotify track titles and artist names.
    """
    tracks = []
    for track in result["items"]:
        title = track["track"]["name"]
        artists = ", ".join([y["name"] for y in track["track"]["artists"]])
        tracks.append(
            f"{artists} - {title}" if artist_first else f"{title} - {artists}"
        )

    return tracks


def compute_distance(
    spotify_playlist: str,
    spotify_track: str,
    beatcloud_track: str,
    threshold: float,
) -> Tuple[str, float]:
    """Qualifies a match between a Spotify track and a beatcloud track using
        Levenshtein similarity.

    Args:
        spotify_playlist: Playlist that Spotify track belongs to.
        spotify_track: Spotify track title and artist name.
        beatcloud_track: Beatcloud track title and artist name
        threshold: Levenshtein similarity threshold for acceptance.

    Returns:
        Tuple of Spotify playlist, Spotify "TRACK TITLE - ARTIST NAME",
            beatcloud "TRACK TITLE - ARTIST NAME", Levenshtein similarity.
    """
    ret = ()
    fuzz_ratio = fuzz.ratio(spotify_track, beatcloud_track)
    if fuzz_ratio >= threshold:
        ret = spotify_playlist, spotify_track, beatcloud_track, fuzz_ratio
    return ret


def find_matches(
    spotify_tracks: Dict[str, Set[str]],
    beatcloud_tracks: List[str],
    config: BaseConfig,
) -> List[Tuple[str, float]]:
    """Computes the Levenshtein similarity between the product of all beatcloud
        tracks with all the tracks in the given Spotify playlist(s) and returns
        those that match above a threshold.

    Args:
        spotify_tracks: Spotify track titles and artist names.
        beatcloud_tracks: Beatcloud track titles and artist names.
        config: Configuration object.

    Returns:
        List of tuples of Spotify playlist, Spotify track, Beatcloud track, and
            Levenshtein distance.
    """
    spotify_tracks = [
        (playlist, track) for playlist, tracks in spotify_tracks.items()
        for track in tracks
    ]
    _product = list(product(spotify_tracks, beatcloud_tracks))
    _temp, beatcloud_tracks = zip(*_product)
    spotify_playlists, spotify_tracks = zip(*_temp)
    fuzz_ratio = config.CHECK_TRACKS_FUZZ_RATIO
    payload = [
        spotify_playlists,
        spotify_tracks,
        beatcloud_tracks,
        [fuzz_ratio] * len(_product),
    ]
    with ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as executor:
        matches = list(
            filter(
                None,
                tqdm(
                    executor.map(compute_distance, *payload),
                    total=len(_product),
                    desc="Matching new and Beatcloud tracks",
                )
            )
        )

    return matches


def get_beatcloud_tracks() -> List[str]:
    """Lists all the music files in S3 and parses out the track titles and
        artist names.
    
    Returns:
        Beatcloud track titles and artist names.
    """
    cmd = ["aws", "s3", "ls", "--recursive", "s3://dj.beatcloud.com/dj/music/"]
    output = check_output(cmd).decode("utf-8").split("\n")
    tracks = [Path(track) for track in output if track]
    logger.info(f"Got {len(tracks)} tracks from the beatcloud")

    return tracks


def get_local_tracks(config: BaseConfig) -> Dict[str, List[str]]:
    """Aggregates the files from one or more local directories in a dictionary
        mapped with parent directories.

    Args:
        config: Configuration object.

    Returns:
        Local file names keyed by parent directory.
    """
    local_dir_tracks = {}
    for _dir in config.CHECK_TRACKS_LOCAL_DIRS:
        if not _dir.exists():
            logger.warning(
                f"{_dir} does not exist; will not be able to check its "
                "contents against the beatcloud"
            )
            continue
        files = [_file.stem for _file in _dir.rglob("**/*.*")]
        if files:
            local_dir_tracks[_dir] = files
    local_tracks_count = sum(len(x) for x in local_dir_tracks.values())
    logger.info(f"Got {local_tracks_count} files under local directories")

    return local_dir_tracks


def get_playlist_tracks(
    spotify: spotipy.Spotify, playlist_id: str, artist_first: bool
) -> Set[str]:
    """Queries Spotify API for a playlist and pulls tracks from it.

    Args:
        spotify: Spotify client.
        playlist_id: Playlist ID of Spotify playlist to pull tracks from.
        artist_first: Whether or not artist should come before track title.

    Raises:
        RuntimeError: Playlist_id must correspond with a valid Spotify playlist.

    Returns:
        Spotify track titles and artist names from a given playlist.
    """
    try:
        playlist = spotify.playlist(playlist_id)
    except Exception:
        raise RuntimeError(
            f"Failed to get playlist with ID {playlist_id}"
        ) from Exception

    result = playlist["tracks"]
    tracks = add_tracks(result, artist_first)

    while result["next"]:
        result = spotify.next(result)
        tracks.extend(add_tracks(result, artist_first))

    return set(tracks)


def get_spotify_tracks(config: BaseConfig) -> Dict[str, Set[str]]:
    """Aggregates the tracks from one or more Spotify playlists into a
        dictionary mapped with playlist names.

    Args:
        config: Configuration object.
    
    Returns:
        Spotify track titles and artist names keyed by playlist name.
    """
    spotify = get_spotify_client(config)
    playlist_ids = get_playlist_ids()

    playlist_tracks = {}
    _sum = 0
    for playlist in config.CHECK_TRACKS_SPOTIFY_PLAYLISTS:
        playlist_id = playlist_ids.get(playlist)
        if not playlist_id:
            logger.error(f"{playlist} not in spotify_playlists.yaml")
            continue

        playlist_tracks[playlist] = get_playlist_tracks(
            spotify, playlist_id, config.ARTIST_FIRST
        )
        length = len(playlist_tracks[playlist])
        logger.info(
            f'Got {length} track{"" if length == 1 else "s"} from Spotify '
            f'playlist "{playlist}"'
        )
        _sum += length

        if config.VERBOSITY > 0:
            for track in playlist_tracks[playlist]:
                logger.info(f"\t{track}")
    logger.info(
        f'Got {_sum} track{"" if _sum == 1 else "s"} from Spotify in total'
    )

    return playlist_tracks


def initialize_logger() -> Tuple[logging.Logger, str]:
    """Initializes logger from configuration.

    Returns:
        Tuple containing Logger and associated log file.
    """
    log_file = (
        Path(__file__).parent.parent / "logs" /
        f'{datetime.now().strftime("%Y-%m-%d")}.log'
    )
    log_conf = Path(__file__).parent.parent / "configs" / "logging.conf"
    logging.config.fileConfig(
        fname=log_conf,
        # NOTE(a-rich): the `logfilename` needs a unix-style path.
        defaults={"logfilename": log_file.as_posix()},
        disable_existing_loggers=False,
    )

    return logging.getLogger(__name__), log_file


def mock_exists(files, path):
    """Function for mocking the existence of pathlib.Path object."""
    ret = True
    for file_name, exists in files:
        if file_name == path.name:
            ret = exists
            break
    return ret


def reverse_title_and_artist(path_lookup: Dict[str, str]) -> Dict[str, str]:
    """Reverses the title and artist parts of the filename.

    Args:
        path_lookup: Mapping of filenames to file paths.

    Returns:
        Mapping with the title and artist in the filenames reversed.
    """
    new_path_lookup = {}
    for key, value in path_lookup.items():
        split = key.split(" - ")
        title = " - ".join(split[:-1])
        artist = split[-1]
        new_path_lookup[f"{artist} - {title}"] = value

    return new_path_lookup
