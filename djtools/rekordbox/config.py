"""This module contains the configuration object for the rekordbox package.
The attributes of this configuration object correspond with the "rekordbox" key
of config.yaml
"""
import logging
from pathlib import Path
from typing import List

from djtools.configs.config import BaseConfig


logger = logging.getLogger(__name__)


class RekordboxConfig(BaseConfig):
    """Configuration object for the rekordbox package."""

    BUILD_PLAYLISTS: bool = False
    BUILD_PLAYLISTS_REMAINDER: str = "folder"
    COPY_PLAYLISTS:  List[str] = []
    COPY_PLAYLISTS_DESTINATION: Path = None
    PURE_GENRE_PLAYLISTS:  List[str] = []
    SHUFFLE_PLAYLISTS:  List[str] = []

    def __init__(self, *args, **kwargs):
        """Constructor.
        
        Raises:
            RuntimeError: XML_PATH must be a valid rekordbox XML file.
            RuntimeError: rekordbox_playlists.yaml must be a valid YAML file.
        """
        super().__init__(*args, **kwargs)

        if any(
            [
                self.BUILD_PLAYLISTS,
                self.COPY_PLAYLISTS,
                self.SHUFFLE_PLAYLISTS,
            ]
        ) and (not self.XML_PATH or not self.XML_PATH.exists()):
            raise RuntimeError(
                "Using the rekordbox package requires the config option "
                "XML_PATH to be a valid rekordbox XML file"
            )

        if self.BUILD_PLAYLISTS:
            playlist_config = (
                Path(__file__).parent.parent / "configs" /
                "rekordbox_playlists.yaml"
            )
            if not playlist_config.exists():
                raise RuntimeError(
                    "rekordbox_playlists.yaml must be a valid YAML to use the "
                    "BUILD_PLAYLISTS feature"
                )
