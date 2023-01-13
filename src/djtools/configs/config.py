"""This module contains the base configuration object. All the attributes of
this configuration object either don't apply to any particular package or they
apply to multiple packages. The attributes of this configuration object
correspond with the "configs" key of config.yaml."""
import logging
import os
from typing_extensions import Literal

from pydantic import BaseModel, Extra, NonNegativeInt


logger = logging.getLogger(__name__)


class BaseConfig(BaseModel, extra=Extra.allow):
    """Base configuration object used across the whole library."""

    AWS_PROFILE: str = "default"
    LOG_LEVEL: Literal[
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    ] = "INFO"
    VERBOSITY: NonNegativeInt = 0
    XML_PATH: str = ""

    def __init__(self, *args, **kwargs):
        """Constructor.
        
        Raises:
            RuntimeError: awscli must be installed.
            RuntimeError: AWS_PROFILE must be valid.
            RuntimeError: SPOTIFY_CLIENT_ID, SPOTFIY_CLIENT_SECRET, and
                SPOTIFY_REDIRECT_URI must all be valid.
        """
        super().__init__(*args, **kwargs)
        logger.info(repr(self))
        if self.__class__.__name__ != "BaseConfig":
            return

        if not self.AWS_PROFILE:
            logger.warning(
                "Without AWS_PROFILE set to a valid profile ('default' or "
                "otherwise) you cannot use any of the following features: "
                "CHECK_TRACKS, DOWNLOAD_MUSIC, DOWNLOAD_XML, UPLOAD_MUSIC, "
                "UPLOAD_XML"
            )
        else:
            os.environ["AWS_PROFILE"] = self.AWS_PROFILE
            # TODO(a-rich): Figure out why awscli fails in the test runner.
            # cmd = "aws s3 ls s3://dj.beatcloud.com/"
            # try:
            #     proc = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
            # except Exception as exc:
            #     raise RuntimeError(
            #         "Failed to run AWS command; make sure you've installed "
            #         "awscli correctly."
            #     )
            # _, stderr = proc.communicate()
            # stderr = stderr.decode("utf-8").strip("\n")
            # if stderr == (
            #     f"The config profile ({self.AWS_PROFILE}) could not be found"
            # ):
            #     raise RuntimeError("AWS_PROFILE is not a valid profile!")
        
        if not self.XML_PATH:
            logger.warning(
                "XML_PATH is not set. Without this set to a valid Rekordbox "
                "XML export, you cannot use the following features: "
                "COPY_PLAYLISTS, DOWNLOAD_XML, RANDOMIZE_PLAYLISTS, "
                "REKORDBOX_PLAYLISTS, UPLOAD_XML"
            )
        elif not os.path.exists(self.XML_PATH):
            logger.warning(
                "XML_PATH does not exist. Without this set to a valid "
                "Rekordbox XML export, you cannot use the following features: "
                "COPY_PLAYLISTS, DOWNLOAD_XML, RANDOMIZE_PLAYLISTS, "
                "REKORDBOX_PLAYLISTS, UPLOAD_XML"
            )
