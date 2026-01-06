"""This module contains the configuration objects for the collection package.
The attributes of this configuration object correspond with the "collection"
key of config.yaml
"""

import logging
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from pydantic import BaseModel, Field, PositiveInt, ValidationError

from djtools.configs.config_formatter import BaseConfigFormatter

logger = logging.getLogger(__name__)


class PlaylistFilters(Enum):
    """PlaylistFilters enum."""

    COMPLEX_TRACK_FILTER = "ComplexTrackFilter"
    HIPHOP_FILTER = "HipHopFilter"
    MINIMAL_DEEP_TECH_FILTER = "MinimalDeepTechFilter"
    TRANSITION_TRACK_FILTER = "TransitionTrackFilter"


def playlist_filter_representer(dumper, data):
    # pylint: disable=missing-function-docstring
    return dumper.represent_scalar(  # pragma: no cover
        "!PlaylistFilters", data.value
    )


def playlist_filter_constructor(loader, node):
    # pylint: disable=missing-function-docstring
    return PlaylistFilters(loader.construct_scalar(node))  # pragma: no cover


yaml.add_representer(PlaylistFilters, playlist_filter_representer)
yaml.add_constructor("!PlaylistFilters", playlist_filter_constructor)


class PlaylistRemainder(Enum):
    """PlaylistRemainder enum."""

    FOLDER = "folder"
    PLAYLIST = "playlist"


def playlist_remainder_representer(dumper, data):
    # pylint: disable=missing-function-docstring
    return dumper.represent_scalar("!PlaylistRemainder", data.value)


def playlist_remainder_constructor(loader, node):
    # pylint: disable=missing-function-docstring
    return PlaylistRemainder(loader.construct_scalar(node))


yaml.add_representer(PlaylistRemainder, playlist_remainder_representer)
yaml.add_constructor("!PlaylistRemainder", playlist_remainder_constructor)


class RegisteredPlatforms(Enum):
    """RegisteredPlatforms enum."""

    REKORDBOX = "rekordbox"


def registered_platforms_representer(dumper, data):
    # pylint: disable=missing-function-docstring
    return dumper.represent_scalar("!RegisteredPlatforms", data.value)


def registered_platforms_constructor(loader, node):
    # pylint: disable=missing-function-docstring
    return RegisteredPlatforms(loader.construct_scalar(node))


yaml.add_representer(RegisteredPlatforms, registered_platforms_representer)
yaml.add_constructor("!RegisteredPlatforms", registered_platforms_constructor)


class CollectionConfig(BaseConfigFormatter):
    """Configuration object for the collection package."""

    collection_path: Optional[Path] = None
    collection_playlist_filters: List[PlaylistFilters] = Field(
        default_factory=list
    )
    collection_playlists: bool = False
    collection_playlists_remainder: PlaylistRemainder = (
        PlaylistRemainder.FOLDER
    )
    copy_playlists: List[str] = Field(default_factory=list)
    copy_playlists_destination: Optional[Path] = None
    minimum_combiner_playlist_tracks: Optional[PositiveInt] = None
    minimum_tag_playlist_tracks: Optional[PositiveInt] = None
    platform: RegisteredPlatforms = RegisteredPlatforms.REKORDBOX
    shuffle_playlists: List[str] = Field(default_factory=list)
    playlist_config: Optional["PlaylistConfig"] = None

    def __init__(self, *args, **kwargs):
        """Constructor.

        Raises:
            RuntimeError: Using the collection package requires a valid
                collection_path.
            RuntimeError: Failed to render collection_playlist.yaml from
                template.
            RuntimeError: collection_path must be a valid collection path.
            RuntimeError: collection_playlists.yaml must be a valid YAML file.
        """
        super().__init__(*args, **kwargs)

        if any(
            [
                self.collection_playlists,
                self.copy_playlists,
                self.shuffle_playlists,
            ]
        ) and (not self.collection_path or not self.collection_path.exists()):
            raise RuntimeError(
                "Using the collection package requires the config option "
                "collection_path to be a valid collection path"
            )

        if self.collection_playlists:
            config_path = Path(__file__).parent.parent / "configs"
            env = Environment(
                loader=FileSystemLoader(config_path / "playlist_templates")
            )
            playlist_template = None
            playlist_template_name = "collection_playlists.j2"
            playlist_config_path = config_path / "collection_playlists.yaml"

            try:
                playlist_template = env.get_template(playlist_template_name)
            except TemplateNotFound:
                pass

            if playlist_template:
                try:
                    playlist_config = playlist_template.render()
                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to render {playlist_template_name}: {exc}"
                    ) from exc

                if playlist_config_path.exists():
                    logger.warning(
                        f"Both {playlist_template_name} and "
                        f"{playlist_config_path.name} exist. Overwriting "
                        f"{playlist_config_path.name} with the rendered "
                        "template"
                    )

                with open(
                    playlist_config_path, mode="w", encoding="utf-8"
                ) as _file:
                    _file.write(playlist_config)

            if not playlist_config_path.exists():
                raise RuntimeError(
                    "collection_playlists.yaml must exist to use the "
                    "collection_playlists feature"
                )

            try:
                with open(
                    playlist_config_path, mode="r", encoding="utf-8"
                ) as _file:
                    self.playlist_config = PlaylistConfig(
                        **yaml.load(_file, Loader=yaml.FullLoader) or {}
                    )
            except ValidationError as exc:
                raise RuntimeError(
                    "collection_playlists.yaml must be a valid YAML to use "
                    "the collection_playlists feature"
                ) from exc


class PlaylistName(BaseModel, extra="forbid"):
    "A class for configuring the names of playlists."

    tag_content: str
    name: Optional[str] = None


class PlaylistConfigContent(BaseModel, extra="forbid"):
    "A class for type checking the content of the playlist config YAML."

    name: str
    playlists: List[Union["PlaylistConfigContent", PlaylistName, str]]
    enable_aggregation: Optional[bool] = None


class PlaylistConfig(BaseModel, extra="forbid"):
    "A class for type checking the playlist config YAML."

    combiner: Optional[PlaylistConfigContent] = None
    tags: Optional[PlaylistConfigContent] = None
