"""This module is responsible for syncing tracks between "USB_PATH" and the
Beatcloud (upload and download). It also handles uploading the collection
located at "COLLECTION_PATH" and downloading the collection uploaded to the
Beatcloud by "IMPORT_USER" before modifying it to point to track locations at
"USB_PATH".
"""

import logging
from os.path import getmtime
from pathlib import Path
from subprocess import Popen
from typing import List, Optional, Type

from djtools.sync.helpers import (
    parse_sync_command,
    rewrite_track_paths,
    run_sync,
    webhook,
)
from djtools.utils.check_tracks import compare_tracks


logger = logging.getLogger(__name__)
BaseConfig = Type["BaseConfig"]


def download_music(
    config: BaseConfig, beatcloud_tracks: Optional[List[str]] = None
):
    """This function syncs tracks from the Beatcloud to "USB_PATH".

    If "DOWNLOAD_SPOTIFY_PLAYLIST" is set to a playlist name that exists in
    "spotify_playlists.yaml", then "DOWNLOAD_INCLUDE_DIRS" will be populated
    with tracks in that playlist that match Beatcloud tracks.

    Args:
        config: Configuration object.
        beatcloud_tracks: List of track artist - titles from S3.
    """
    if config.sync.DOWNLOAD_SPOTIFY_PLAYLIST:
        playlist_name = config.sync.DOWNLOAD_SPOTIFY_PLAYLIST
        user = playlist_name.split("Uploads")[0].strip()
        beatcloud_tracks, beatcloud_matches = compare_tracks(
            config,
            beatcloud_tracks=beatcloud_tracks,
        )
        if not beatcloud_matches:
            logger.warning(
                "No Beatcloud matches were found! Make sure you've supplied "
                "the correct playlist name."
            )
            return beatcloud_tracks
        config.sync.DOWNLOAD_INCLUDE_DIRS = [
            (Path(user) / path.as_posix().split(f"{Path(user)}/")[-1])
            for path in beatcloud_matches
        ]
        config.sync.DOWNLOAD_EXCLUDE_DIRS = []

    logger.info("Downloading track collection...")
    dest = Path(config.sync.USB_PATH) / "DJ Music"
    glob_path = (Path("**") / "*.*").as_posix()
    old = {str(p) for p in dest.rglob(glob_path)}
    logger.info(f"Found {len(old)} files at {config.sync.USB_PATH}")

    dest.mkdir(parents=True, exist_ok=True)
    cmd = [
        "aws",
        "s3",
        "sync",
        f"{config.sync.BUCKET_URL}/dj/music/",
        dest.as_posix(),
    ]
    run_sync(parse_sync_command(cmd, config), config.sync.BUCKET_URL)

    new = {str(p) for p in dest.rglob(glob_path)}
    difference = sorted(list(new.difference(old)), key=getmtime)
    if difference:
        logger.info(f"Found {len(difference)} new files")
        for diff in difference:
            logger.info(f"\t{diff}")

    return beatcloud_tracks


def download_collection(config: BaseConfig):
    """This function downloads the collection of "IMPORT_USER".

    After downloading "IMPORT_USER"'s collection, the location of all the
    tracks are modified so that they point to USER's "USB_PATH".

    Args:
        config: Configuration object.
    """
    logger.info(
        f"Downloading {config.sync.IMPORT_USER}'s {config.sync.PLATFORM} collection..."
    )
    collection_dir = config.sync.COLLECTION_PATH.parent
    src = (
        f"{config.sync.BUCKET_URL}/dj/collections/{config.sync.IMPORT_USER}/"
        f"{config.collection.PLATFORM}_collection"
    )
    dst = (
        Path(collection_dir)
        / f"{config.sync.IMPORT_USER}_{config.collection.COLLECTION_PATH.name}"
    )
    cmd = ["aws", "s3", "cp", src, dst.as_posix()]
    if config.collection.COLLECTION_PATH.is_dir():
        cmd.append("--recursive")
    logger.info(" ".join(cmd))
    with Popen(cmd) as proc:
        proc.wait()
    if config.sync.USER != config.sync.IMPORT_USER:
        rewrite_track_paths(config, dst)


def upload_music(config: BaseConfig):
    """This function syncs tracks from "USB_PATH" to the Beatcloud.

    "AWS_USE_DATE_MODIFIED" can be used in order to re-upload tracks that
    already exist in the Beatcloud but have been modified since the last time
    they were uploaded (i.e. ID3 tags have been altered).

    Args:
        config: Configuration object.
    """
    hidden_files = set(
        (Path(config.sync.USB_PATH) / "DJ Music").rglob(
            (Path("**") / ".*.*").as_posix()
        )
    )
    if hidden_files:
        logger.info(f"Removed {len(hidden_files)} files...")
        for _file in hidden_files:
            logger.info(f"\t{_file}")
            _file.unlink()

    logger.info("Uploading track collection...")
    src = (Path(config.sync.USB_PATH) / "DJ Music").as_posix()
    cmd = ["aws", "s3", "sync", src, f"{config.sync.BUCKET_URL}/dj/music/"]

    if config.sync.DISCORD_URL and not config.sync.DRYRUN:
        webhook(
            config.sync.DISCORD_URL,
            content=run_sync(
                parse_sync_command(cmd, config, upload=True),
                config.sync.BUCKET_URL,
            ),
        )
    else:
        run_sync(
            parse_sync_command(cmd, config, upload=True),
            config.sync.BUCKET_URL,
        )


def upload_collection(config: BaseConfig):
    """This function uploads "COLLECTION_PATH" to the cloud.

    Args:
        config: Configuration object.
    """
    logger.info(
        f"Uploading {config.sync.USER}'s {config.collection.PLATFORM} collection..."
    )
    dst = (
        f"{config.sync.BUCKET_URL}/dj/collections/{config.sync.USER}/"
        f"{config.collection.PLATFORM}_collection"
    )
    cmd = [
        "aws",
        "s3",
        "cp",
        config.collection.COLLECTION_PATH.as_posix(),
        dst,
    ]
    if config.collection.COLLECTION_PATH.is_dir():
        cmd.append("--recursive")
    logger.info(" ".join(cmd))
    with Popen(cmd) as proc:
        proc.wait()
