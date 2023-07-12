"""This module contains the base configuration object. All the attributes of
this configuration object either don't apply to any particular package or they
apply to multiple packages. The attributes of this configuration object
correspond with the "configs" key of config.yaml."""
import logging
import os
from pathlib import Path
from typing_extensions import Literal

from pydantic import BaseModel, Extra, NonNegativeInt


logger = logging.getLogger(__name__)


class BaseConfig(BaseModel, extra=Extra.allow):
    """Base configuration object used across the whole library."""

    AWS_PROFILE: str = "default"
    COLLECTION_PATH: Path = None
    LOG_LEVEL: Literal[
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    ] = "INFO"
    VERBOSITY: NonNegativeInt = 0

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super().__init__(*args, **kwargs)
        logger.info(repr(self))
        if type(self) is not BaseConfig:  # pylint: disable=unidiomatic-typecheck
            return

        if not self.AWS_PROFILE:
            logger.warning(
                "Without AWS_PROFILE set to a valid profile ('default' or "
                "otherwise) you cannot use any of the following features: "
                "CHECK_TRACKS, DOWNLOAD_MUSIC, DOWNLOAD_COLLECTION, "
                "UPLOAD_MUSIC, UPLOAD_COLLECTION"
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

        if not self.COLLECTION_PATH:
            logger.warning(
                "COLLECTION_PATH is not set. Without this set to a valid "
                "collection, you cannot use the following features: "
                "COLLECTION_PLAYLISTS, COPY_PLAYLISTS, DOWNLOAD_COLLECTION, "
                "SHUFFLE_PLAYLISTS, UPLOAD_COLLECTION"
            )
        elif not self.COLLECTION_PATH.exists():
            logger.warning(
                "COLLECTION_PATH does not exist. Without this set to a valid "
                "collection, you cannot use the following features: "
                "COLLECTION_PLAYLISTS, COPY_PLAYLISTS, DOWNLOAD_COLLECTION, "
                "SHUFFLE_PLAYLISTS, UPLOAD_COLLECTION"
            )

    def __repr__(self):
        super_keys = set(BaseConfig.__fields__)
        ret = f"{self.__class__.__name__}("
        for name, value in self.dict().items():
            if (
                (name in super_keys and type(self) is not BaseConfig)  # pylint: disable=unidiomatic-typecheck
                or (name not in super_keys and type(self) is BaseConfig)  # pylint: disable=unidiomatic-typecheck
            ):
                continue
            if (
                isinstance(value, list) and len(value) > 1
                and isinstance(value[0], (dict, list, set))
            ):
                ret += f"\n\t{name}=[\n\t\t"
                ret += "\n\t\t".join(str(v) for v in value)
                ret += "\n\t]"
                continue
            ret += f"\n\t{name}={str(value)}"
        ret += "\n)"

        return ret
