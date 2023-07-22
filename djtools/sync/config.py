"""This module contains the configuration object for the sync package.
The attributes of this configuration object correspond with the "sync" key
of config.yaml
"""
import getpass
import logging
import os
from pathlib import Path
from typing import List, Optional, Union

from pydantic import validator

from djtools.configs.config import BaseConfig


logger = logging.getLogger(__name__)


class SyncConfig(BaseConfig):
    """Configuration object for the sync package."""

    ARTIST_FIRST: bool = False
    AWS_PROFILE: str = "default"
    AWS_USE_DATE_MODIFIED: bool = False
    DISCORD_URL: str = ""
    DOWNLOAD_COLLECTION: bool = False
    DOWNLOAD_EXCLUDE_DIRS: List[Path] = []
    DOWNLOAD_INCLUDE_DIRS: List[Path] = []
    DOWNLOAD_MUSIC: bool = False
    DOWNLOAD_SPOTIFY_PLAYLIST: str = ""
    DRYRUN: bool = False
    IMPORT_USER: str = ""
    UPLOAD_COLLECTION: bool = False
    UPLOAD_EXCLUDE_DIRS: List[Path] = []
    UPLOAD_INCLUDE_DIRS: List[Path] = []
    UPLOAD_MUSIC: bool = False
    USB_PATH: Optional[Union[str, Path]] = None
    USER: str = ""

    def __init__(self, *args, **kwargs):
        """Constructor.

        Raises:
            ValueError: Both include and exclude dirs can't be provided at the
                same time.
            RuntimeError: AWS_PROFILE must be set.
        """
        super().__init__(*args, **kwargs)
        if not self.USER:
            self.USER = getpass.getuser()

        if (
            (self.UPLOAD_INCLUDE_DIRS and self.UPLOAD_EXCLUDE_DIRS)
            or (self.DOWNLOAD_INCLUDE_DIRS and self.DOWNLOAD_EXCLUDE_DIRS)
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
                self.DOWNLOAD_COLLECTION,
                self.DOWNLOAD_MUSIC,
                self.UPLOAD_COLLECTION,
                self.UPLOAD_MUSIC,
            ]
        ):
            if not self.AWS_PROFILE:
                msg = "Config must include AWS_PROFILE for sync operations"
                logger.critical(msg)
                raise RuntimeError(msg)

        os.environ["AWS_PROFILE"] = self.AWS_PROFILE

        if any([self.DOWNLOAD_MUSIC, self.UPLOAD_MUSIC]) and not self.USB_PATH:
            msg = (
                "Config must include USB_PATH for both DOWNLOAD_MUSIC and "
                "UPLOAD_MUSIC sync operations"
            )
            logger.critical(msg)
            raise RuntimeError(msg)

        if (
            any([self.DOWNLOAD_MUSIC, self.UPLOAD_MUSIC]) and
            not self.USB_PATH.exists()
        ):
            msg = f'Configured USB_PATH "{self.USB_PATH}" was not found!'
            logger.critical(msg)
            raise RuntimeError(msg)

        if self.UPLOAD_MUSIC and not self.DISCORD_URL:
            logger.warning(
                'DISCORD_URL is not configured...set this for "New Music" '
                "discord messages!"
            )

        if self.DOWNLOAD_COLLECTION and not self.IMPORT_USER:
            raise RuntimeError(
                "IMPORT_USER must be set to download a collection"
            )

    @validator("USB_PATH")
    @classmethod
    def usb_path_as_pathlib_path(cls, value: str) -> Union[Path, str]:
        """Validator to convert USB_PATH to a pathlib.Path.

        Args:
            value: USB_PATH field

        Returns:
            pathlib.Path representing the USB_PATH field or else an empty string.
        """
        return value if not value else Path(value)
