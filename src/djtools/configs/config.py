"""This module contains the base configuration object. All the attributes of
this configuration object either don't apply to any particular package or they
apply to multiple packages. The attributes of this configuration object
correspond with the "configs" key of config.yaml."""

import logging
from typing import Literal

from pydantic import Field, NonNegativeInt

from djtools.collection.config import CollectionConfig
from djtools.configs.config_formatter import BaseConfigFormatter
from djtools.spotify.config import SpotifyConfig
from djtools.sync.config import SyncConfig
from djtools.utils.config import UtilsConfig


logger = logging.getLogger(__name__)


class BaseConfig(BaseConfigFormatter):
    """Base configuration object used across the whole library."""

    collection: CollectionConfig = Field(default_factory=CollectionConfig)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = (
        "INFO"
    )
    spotify: SpotifyConfig = Field(default_factory=SpotifyConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)
    utils: UtilsConfig = Field(default_factory=UtilsConfig)
    verbosity: NonNegativeInt = 0
