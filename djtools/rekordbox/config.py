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

    COPY_PLAYLISTS:  List[str] = []
    COPY_PLAYLISTS_DESTINATION: Path = None
    PURE_GENRE_PLAYLISTS:  List[str] = []
    RANDOMIZE_PLAYLISTS:  List[str] = []
    REKORDBOX_PLAYLISTS: bool = False 
    REKORDBOX_PLAYLISTS_REMAINDER: str = "folder"

    def __init__(self, *args, **kwargs):
        """Constructor.
        
        Raises:
            RuntimeError: XML_PATH must be a valid rekordbox XML file.
            RuntimeError: rekordbox_playlists.yaml must be a valid YAML file.
        """
        super().__init__(*args, **kwargs)

        if any(
            [
                self.COPY_PLAYLISTS,
                self.RANDOMIZE_PLAYLISTS,
                self.REKORDBOX_PLAYLISTS,
            ]
        ) and (not self.XML_PATH or not self.XML_PATH.exists()):
            raise RuntimeError(
                "Using the rekordbox package requires the config option "
                "XML_PATH to be a valid rekordbox XML file"
            )

        if self.REKORDBOX_PLAYLISTS:
            playlist_config = (
                Path(__file__).parent.parent / "configs" /
                "rekordbox_playlists.yaml"
            )
            if not playlist_config.exists():
                raise RuntimeError(
                    "rekordbox_playlists.yaml must be a valid YAML to use the "
                    "REKORDBOX_PLAYLISTS feature"
                )
