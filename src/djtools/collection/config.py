"""This module contains the configuration objects for the collection package.
The attributes of this configuration object correspond with the "collection"
key of config.yaml
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import List, Optional, Union
from typing_extensions import Literal

from pydantic import BaseModel, ValidationError
import yaml

from djtools.configs.config import BaseConfig


logger = logging.getLogger(__name__)


class CollectionConfig(BaseConfig):
    """Configuration object for the collection package."""

    COLLECTION_PATH: Optional[Path] = None
    COLLECTION_PLAYLIST_FILTERS: List[
        Literal[
            "HipHopFilter",
            "MinimalDeepTechFilter",
            "ComplexTrackFilter",
            "TransitionTrackFilter",
        ]
    ] = []
    COLLECTION_PLAYLISTS: bool = False
    COLLECTION_PLAYLISTS_REMAINDER: Literal["folder", "playlist"] = "folder"
    COPY_PLAYLISTS: List[str] = []
    COPY_PLAYLISTS_DESTINATION: Optional[Path] = None
    PLATFORM: Literal["rekordbox"] = "rekordbox"
    SHUFFLE_PLAYLISTS: List[str] = []

    def __init__(self, *args, **kwargs):
        """Constructor.

        Raises:
            RuntimeError: COLLECTION_PATH must be a valid collection path.
            RuntimeError: collection_playlists.yaml must be a valid YAML file.
        """
        super().__init__(*args, **kwargs)

        if any(
            [
                self.COLLECTION_PLAYLISTS,
                self.COPY_PLAYLISTS,
                self.SHUFFLE_PLAYLISTS,
            ]
        ) and (not self.COLLECTION_PATH or not self.COLLECTION_PATH.exists()):
            raise RuntimeError(
                "Using the collection package requires the config option "
                "COLLECTION_PATH to be a valid collection path"
            )

        if self.COLLECTION_PLAYLISTS:
            playlist_config_path = (
                Path(__file__).parent.parent
                / "configs"
                / "collection_playlists.yaml"
            )
            if not playlist_config_path.exists():
                raise RuntimeError(
                    "collection_playlists.yaml must exist to use the "
                    "COLLECTION_PLAYLISTS feature"
                )
            try:
                with open(
                    playlist_config_path, mode="r", encoding="utf-8"
                ) as _file:
                    PlaylistConfig(
                        **yaml.load(_file, Loader=yaml.FullLoader) or {}
                    )
            except ValidationError as exc:
                raise RuntimeError(
                    "collection_playlists.yaml must be a valid YAML to use "
                    "the COLLECTION_PLAYLISTS feature"
                ) from exc


class PlaylistName(BaseModel, extra="forbid"):
    "A class for configuring the names of playlists."
    tag_content: str
    name: Optional[str] = None


class PlaylistConfigContent(BaseModel, extra="forbid"):
    "A class for type checking the content of the playlist config YAML."
    name: str
    playlists: List[Union[PlaylistConfigContent, PlaylistName, str]]


class PlaylistConfig(BaseModel, extra="forbid"):
    "A class for type checking the playlist config YAML."
    combiner: Optional[PlaylistConfigContent] = None
    tags: Optional[PlaylistConfigContent] = None
