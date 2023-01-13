"""This module is responsible for syncing tracks between "USB_PATH" and the
beatcloud (upload and download). It also handles uploading the Rekordbox XML
located at "XML_PATH" and downloading the Rekordbox XML uploaded to the
beatcloud by "IMPORT_USER" before modifying it to point to track locations at
"USB_PATH".
"""
import logging
import os
from pathlib import Path
from typing import List

from djtools.configs.config import BaseConfig
from djtools.sync.helpers import (
    parse_sync_command, rewrite_xml, run_sync, webhook
)
from djtools.utils.check_tracks import compare_tracks
from djtools.utils.helpers import make_dirs


logger = logging.getLogger(__name__)


def download_music(config: BaseConfig, beatcloud_tracks: List[str] = []):
    """This function syncs tracks from the beatcloud to "USB_PATH".

    If "DOWNLOAD_SPOTIFY" is set to a playlist name that exists in
    "spotify_playlists.yaml", then "DOWNLOAD_INCLUDE_DIRS" will be populated
    with tracks in that playlist that match Beatcloud tracks.

    Args:
        config: Configuration object.
        beatcloud_tracks: List of track artist - titles from S3.
    """
    if config.DOWNLOAD_SPOTIFY:
        user = config.DOWNLOAD_SPOTIFY.split("Uploads")[0].strip()
        beatcloud_tracks, beatcloud_matches = compare_tracks(
            config,
            beatcloud_tracks=beatcloud_tracks,
            download_spotify_playlist=config.DOWNLOAD_SPOTIFY,
        )
        config.DOWNLOAD_INCLUDE_DIRS = [
            os.path.join(
                user,
                path.split(os.path.join(user, "").replace(os.sep, "/"))[-1]
            )
            for path in beatcloud_matches
        ]
        config.DOWNLOAD_EXCLUDE_DIRS = []

    dest = os.path.join(config.USB_PATH, "DJ Music").replace(os.sep, "/")
    glob_path = Path(dest)
    old = {
        str(p) for p in glob_path.rglob(
            os.path.join("**", "*.*").replace(os.sep, "/")
        )
    }
    logger.info(f"Found {len(old)} files")

    logger.info("Syncing remote track collection...")
    make_dirs(dest)
    cmd = ["aws", "s3", "sync", "s3://dj.beatcloud.com/dj/music/", dest]
    run_sync(parse_sync_command(cmd, config))

    new = {
        str(p) for p in glob_path.rglob(
            os.path.join("**", "*.*").replace(os.sep, "/")
        )
    }
    difference = sorted(list(new.difference(old)), key=os.path.getmtime)
    if difference:
        logger.info(f"Found {len(difference)} new files")
        for diff in difference:
            logger.info(f"\t{diff}")
    
    return beatcloud_tracks


def download_xml(config: BaseConfig):
    """This function downloads the beatcloud XML of "IMPORT_USER" and modifies
        the "Location" field of all the tracks so that it points to USER's
        "USB_PATH".

    Args:
        config: Configuration object.
    """
    logger.info("Syncing remote rekordbox.xml...")
    xml_dir = os.path.dirname(config.XML_PATH)
    make_dirs(xml_dir)
    _file = f'{config.IMPORT_USER}_rekordbox.xml'
    _file = os.path.join(xml_dir, _file).replace(os.sep, "/")
    cmd = (
        "aws s3 cp s3://dj.beatcloud.com/dj/xml/"
        f'{config.IMPORT_USER}/rekordbox.xml {_file}'
    )
    logger.info(cmd)
    os.system(cmd)
    if config.USER != config.IMPORT_USER:
        rewrite_xml(config)


def upload_music(config: BaseConfig):
    """This function syncs tracks from "USB_PATH" to the beatcloud.
        "AWS_USE_DATE_MODIFIED" can be used in order to reupload tracks that
        already exist in the beatcloud but have been modified since the last
        time they were uploaded (i.e. ID3 tags have been altered).

    Args:
        config: Configuration object.
    """
    glob_path = Path(
        os.path.join(config.USB_PATH, "DJ Music").replace(os.sep, "/")
    )
    hidden_files = {
        str(p) for p in glob_path.rglob(
            os.path.join("**", ".*.*").replace(os.sep, "/")
        )
    }
    if hidden_files:
        logger.info(f"Removed {len(hidden_files)} files...")
        for _file in hidden_files:
            logger.info(f"\t{_file}")
            os.remove(_file)

    logger.info("Syncing track collection...")
    src = os.path.join(config.USB_PATH, "DJ Music").replace(os.sep, "/")
    cmd = ["aws", "s3", "sync", src, "s3://dj.beatcloud.com/dj/music/"]

    if config.DISCORD_URL and not config.DRYRUN:
        webhook(
            config.DISCORD_URL,
            content=run_sync(parse_sync_command(cmd, config, upload=True)),
        )
    else:
        run_sync(parse_sync_command(cmd, config, upload=True))


def upload_xml(config: BaseConfig):
    """This function uploads "XML_PATH" to beatcloud.

    Args:
        config: Configuration object.
    """
    logger.info(f"Uploading {config.USER}'s rekordbox.xml...")
    dst = f"s3://dj.beatcloud.com/dj/xml/{config.USER}/"
    cmd = f"aws s3 cp {config.XML_PATH} {dst}"
    logger.info(cmd)
    os.system(cmd)
