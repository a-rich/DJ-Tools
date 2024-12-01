"""This module contains the configuration objects for the collection package.
The attributes of this configuration object correspond with the "collection"
key of config.yaml
"""

import logging
from pathlib import Path
from typing import List, Literal, Optional, Union

import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from pydantic import BaseModel, PositiveInt, ValidationError

from djtools.configs.config_formatter import BaseConfigFormatter


logger = logging.getLogger(__name__)


class CollectionConfig(BaseConfigFormatter):
    """Configuration object for the collection package."""

    collection_path: Optional[Path] = None
    collection_playlist_filters: List[
        Literal[
            "HipHopFilter",
            "MinimalDeepTechFilter",
            "ComplexTrackFilter",
            "TransitionTrackFilter",
        ]
    ] = []
    collection_playlists: bool = False
    collection_playlists_remainder: Literal["folder", "playlist"] = "folder"
    copy_playlists: List[str] = []
    copy_playlists_destination: Optional[Path] = None
    minimum_combiner_playlist_tracks: Optional[PositiveInt] = None
    minimum_tag_playlist_tracks: Optional[PositiveInt] = None
    platform: Literal["rekordbox"] = "rekordbox"
    shuffle_playlists: List[str] = []
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
