"""This module contains the configuration object for the sync package.
The attributes of this configuration object correspond with the "sync" key
of config.yaml
"""
import getpass
import logging
import os
from typing import Dict, List

import yaml

from djtools.configs.config import BaseConfig


logger = logging.getLogger(__name__)


class SyncConfig(BaseConfig):
    """Configuration object for the sync package."""

    AWS_USE_DATE_MODIFIED: bool = False 
    DISCORD_URL: str = ""
    DOWNLOAD_EXCLUDE_DIRS: List[str] = []
    DOWNLOAD_INCLUDE_DIRS: List[str] = []
    DOWNLOAD_MUSIC: bool = False 
    DOWNLOAD_SPOTIFY: str = ""
    DOWNLOAD_XML: bool = False 
    DRYRUN: bool = False
    IMPORT_USER: str = ""
    UPLOAD_EXCLUDE_DIRS: List[str] = []
    UPLOAD_INCLUDE_DIRS: List[str] = []
    UPLOAD_MUSIC: bool = False 
    UPLOAD_XML: bool = False 
    USB_PATH: str = ""
    USER: str = ""

    def __init__(self, *args, **kwargs):
        """Constructor.

        Raises:
            ValueError: Both include and exclude dirs can't be provided at the
                same time.
            RuntimeError: AWS_PROFILE must be set.
            RuntimeError: registered_users.yaml must be a valid YAML file.
            RuntimeError: IMPORT_USER must exist in registered_users.yaml if
                using DOWNLOAD_XML.
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
                self.DOWNLOAD_MUSIC,
                self.DOWNLOAD_XML,
                self.UPLOAD_MUSIC,
                self.UPLOAD_XML,
            ]
        ):
            if not self.AWS_PROFILE:
                msg = "Config must include AWS_PROFILE for sync operations"
                logger.critical(msg)
                raise RuntimeError(msg)
        
        if self.UPLOAD_MUSIC and not self.DISCORD_URL:
            logger.warning(
                'DISCORD_URL is not configured...set this for "New Music" '
                "discord messages!"
            )

        registered_users_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "configs",
            "registered_users.yaml",
        ).replace(os.sep, "/")
        if os.path.exists(registered_users_path):
            try:
                with open(
                    registered_users_path, mode="r", encoding="utf-8"
                ) as _file:
                    registered_users = (
                        yaml.load(_file, Loader=yaml.FullLoader) or {}
                    )
                logger.info(f"Registered users: {registered_users}")
            except Exception:
                msg = "Error reading registered_users.yaml"
                logger.critical(msg)
                raise RuntimeError(msg) from Exception
        else:
            registered_users = {}
            logger.warning("No registered users!")

        if (
            self.DOWNLOAD_XML and (
                not self.IMPORT_USER or self.IMPORT_USER not in
                registered_users
            )
        ):
            raise RuntimeError(
                "Unable to import from XML of unregistered IMPORT_USER "
                f'"{self.IMPORT_USER}"'
            )

        # Enter USER into "registered_users.yaml".
        registered_users[self.USER] = self.USB_PATH
        with open(registered_users_path, mode="w", encoding="utf-8") as _file:
            yaml.dump(registered_users, _file)
