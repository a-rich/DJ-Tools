"""This module contains the configuration object for the sync package.
The attributes of this configuration object correspond with the "sync" key
of config.yaml
"""

import getpass
import logging
import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel


logger = logging.getLogger(__name__)


class SyncConfig(BaseModel):
    """Configuration object for the sync package."""

    artist_first: bool = False
    aws_profile: str = "default"
    aws_use_date_modified: bool = False
    bucket_url: str = ""
    discord_url: str = ""
    download_collection: bool = False
    download_exclude_dirs: List[Path] = []
    download_include_dirs: List[Path] = []
    download_music: bool = False
    download_spotify_playlist: str = ""
    dryrun: bool = False
    import_user: str = ""
    upload_collection: bool = False
    upload_exclude_dirs: List[Path] = []
    upload_include_dirs: List[Path] = []
    upload_music: bool = False
    usb_path: Optional[Path] = None
    user: str = ""

    def __init__(self, *args, **kwargs):
        """Constructor.

        Raises:
            ValueError: Both include and exclude dirs can't be provided at the
                same time.
            RuntimeError: AWS_PROFILE must be set.
        """
        super().__init__(*args, **kwargs)
        if not self.user:
            self.user = getpass.getuser()

        if (self.upload_include_dirs and self.upload_exclude_dirs) or (
            self.download_include_dirs and self.download_exclude_dirs
        ):
            msg = (
                "Config must neither contain both UPLOAD_INCLUDE_DIRS and "
                "UPLOAD_EXCLUDE_DIRS or both DOWNLOAD_INCLUDE_DIRS and "
                "DOWNLOAD_EXCLUDE_DIRS"
            )
            logger.critical(msg)
            raise ValueError(msg)

        if any(
            [
                self.download_collection,
                self.download_music,
                self.upload_collection,
                self.upload_music,
            ]
        ):
            if not self.aws_profile:
                msg = "Config must include AWS_PROFILE for sync operations"
                logger.critical(msg)
                raise RuntimeError(msg)

            if not self.bucket_url:
                msg = "Config must include BUCKET_URL for sync operations"
                logger.critical(msg)
                raise RuntimeError(msg)

        os.environ["AWS_PROFILE"] = (
            self.aws_profile
        )  # pylint: disable=no-member

        if any([self.download_music, self.upload_music]) and not self.usb_path:
            msg = (
                "Config must include USB_PATH for both DOWNLOAD_MUSIC and "
                "UPLOAD_MUSIC sync operations"
            )
            logger.critical(msg)
            raise RuntimeError(msg)

        if (
            any([self.download_music, self.upload_music])
            and not self.usb_path.exists()
        ):
            msg = f'Configured USB_PATH "{self.usb_path}" was not found!'
            logger.critical(msg)
            raise RuntimeError(msg)

        if self.upload_music and not self.discord_url:
            logger.warning(
                'DISCORD_URL is not configured...set this for "New Music" '
                "discord messages!"
            )

        if self.download_collection and not self.import_user:
            raise RuntimeError(
                "IMPORT_USER must be set to download a collection"
            )
