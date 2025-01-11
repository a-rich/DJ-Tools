"""This module is responsible for syncing tracks between "usb_path" and the
Beatcloud (upload and download). It also handles uploading the collection
located at "collection_path" and downloading the collection uploaded to the
Beatcloud by "import_user" before modifying it to point to track locations at
"usb_path".
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
    """This function syncs tracks from the Beatcloud to "usb_path".

    If "download_spotify_playlist" is set to a playlist name that exists in
    "spotify_playlists.yaml", then "download_include_dirs" will be populated
    with tracks in that playlist that match Beatcloud tracks.

    Args:
        config: Configuration object.
        beatcloud_tracks: List of track artist - titles from S3.
    """
    if config.sync.download_spotify_playlist:
        playlist_name = config.sync.download_spotify_playlist
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
        config.sync.download_include_dirs = [
            (Path(user) / path.as_posix().split(f"{Path(user)}/")[-1])
            for path in beatcloud_matches
        ]
        config.sync.download_exclude_dirs = []

    logger.info("Downloading track collection...")
    dest = Path(config.sync.usb_path) / "DJ Music"
    glob_path = (Path("**") / "*.*").as_posix()
    old = {str(p) for p in dest.rglob(glob_path)}
    logger.info(f"Found {len(old)} files at {config.sync.usb_path}")

    dest.mkdir(parents=True, exist_ok=True)
    cmd = [
        "aws",
        "s3",
        "sync",
        f"{config.sync.bucket_url}/dj/music/",
        dest.as_posix(),
    ]
    run_sync(parse_sync_command(cmd, config), config.sync.bucket_url)

    new = {str(p) for p in dest.rglob(glob_path)}
    difference = sorted(list(new.difference(old)), key=getmtime)
    if difference:
        logger.info(f"Found {len(difference)} new files")
        for diff in difference:
            logger.info(f"\t{diff}")

    return beatcloud_tracks


def download_collection(config: BaseConfig):
    """This function downloads the collection of "import_user".

    After downloading "import_user"'s collection, the location of all the
    tracks are modified so that they point to user's "usb_path".

    Args:
        config: Configuration object.
    """
    logger.info(
        f"Downloading {config.sync.import_user}'s {config.collection.platform.value} collection..."
    )
    collection_dir = config.collection.collection_path.parent
    src = (
        f"{config.sync.bucket_url}/dj/collections/{config.sync.import_user}/"
        f"{config.collection.platform.value}_collection"
    )
    dst = (
        Path(collection_dir)
        / f"{config.sync.import_user}_{config.collection.collection_path.name}"
    )
    cmd = ["aws", "s3", "cp", src, dst.as_posix()]
    if config.collection.collection_path.is_dir():
        cmd.append("--recursive")
    logger.info(" ".join(cmd))
    with Popen(cmd) as proc:
        proc.wait()
    if config.sync.user != config.sync.import_user:
        rewrite_track_paths(config, dst)


def upload_music(config: BaseConfig):
    """This function syncs tracks from "usb_path" to the Beatcloud.

    "aws_use_date_modified" can be used in order to re-upload tracks that
    already exist in the Beatcloud but have been modified since the last time
    they were uploaded (i.e. ID3 tags have been altered).

    Args:
        config: Configuration object.
    """
    hidden_files = set(
        (Path(config.sync.usb_path) / "DJ Music").rglob(
            (Path("**") / ".*.*").as_posix()
        )
    )
    if hidden_files:
        logger.info(f"Removed {len(hidden_files)} files...")
        for _file in hidden_files:
            logger.info(f"\t{_file}")
            _file.unlink()

    logger.info("Uploading track collection...")
    src = (Path(config.sync.usb_path) / "DJ Music").as_posix()
    cmd = ["aws", "s3", "sync", src, f"{config.sync.bucket_url}/dj/music/"]

    if config.sync.discord_url and not config.sync.dryrun:
        webhook(
            config.sync.discord_url,
            content=run_sync(
                parse_sync_command(cmd, config, upload=True),
                config.sync.bucket_url,
            ),
        )
    else:
        run_sync(
            parse_sync_command(cmd, config, upload=True),
            config.sync.bucket_url,
        )


def upload_collection(config: BaseConfig):
    """This function uploads "collection_path" to the cloud.

    Args:
        config: Configuration object.
    """
    logger.info(
        f"Uploading {config.sync.user}'s {config.collection.platform.value} collection..."
    )
    dst = (
        f"{config.sync.bucket_url}/dj/collections/{config.sync.user}/"
        f"{config.collection.platform.value}_collection"
    )
    cmd = [
        "aws",
        "s3",
        "cp",
        config.collection.collection_path.as_posix(),
        dst,
    ]
    if config.collection.collection_path.is_dir():
        cmd.append("--recursive")
    logger.info(" ".join(cmd))
    with Popen(cmd) as proc:
        proc.wait()
