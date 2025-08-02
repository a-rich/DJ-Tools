"""This module contains the base configuration object. All the attributes of
this configuration object either don't apply to any particular package or they
apply to multiple packages. The attributes of this configuration object
correspond with the "configs" key of config.yaml."""

import logging
from enum import Enum

from pydantic import Field, NonNegativeInt
import yaml

from djtools.collection.config import CollectionConfig
from djtools.configs.config_formatter import BaseConfigFormatter
from djtools.spotify.config import SpotifyConfig
from djtools.sync.config import SyncConfig
from djtools.utils.config import UtilsConfig


logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log level Enum."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def log_level_representer(dumper, data):
    # pylint: disable=missing-function-docstring
    return dumper.represent_scalar("!LogLevel", data.value)


def log_level_constructor(loader, node):
    # pylint: disable=missing-function-docstring
    return LogLevel(loader.construct_scalar(node))


yaml.add_representer(LogLevel, log_level_representer)
yaml.add_constructor("!LogLevel", log_level_constructor)


class BaseConfig(BaseConfigFormatter):
    """Base configuration object used across the whole library."""

    collection: CollectionConfig = Field(default_factory=CollectionConfig)
    log_level: LogLevel = LogLevel.INFO
    spotify: SpotifyConfig = Field(default_factory=SpotifyConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)
    utils: UtilsConfig = Field(default_factory=UtilsConfig)
    verbosity: NonNegativeInt = 0

    class Config:
        """Class necessary to support deserializing Enums."""

        extra = "allow"
