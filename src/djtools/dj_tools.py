"""This is the entry point for the DJ Tools library.

Rekordbox operations:
    * COPY_TRACKS_PLAYLISTS (copy_tracks_playlists.py): Copy audio files from
        playlists to a new location and generate a new XML with updated
        Location fields.
    * RANDOMIZE_TRACKS (randomize_tracks.py): Set ID3 tags of tracks in
        playlists sequentially (after shuffling) to randomize.
    * REKORDBOX_PLAYLISTS (rekordbox.playlist_builder.py): Automatically
        create a playlist structure based on the tags present in an XML.

Spotify operations:
    * AUTO_PLAYLIST_UPDATE (spotify.playlist_builder.py): Creating and updating
        Spotify playlists using subreddit top posts.
    * PLAYLISTS_FROM_UPLOAD (spotify.playlist_builder.py): Creating and
        updating Spotify playlists using the Discord webhook output from users
        uploading music.

Utils operations:
    * CHECK_TRACKS (check_tracks.py): Identify overlap between Spotify 
        playlists and / or local directories and and the Beatcloud.
    * YOUTUBE_DL (youtube_dl.py): Download tracks from a URL (e.g. Soundcloud
        playlist).

Sync operations:
    * DOWNLOAD_MUSIC: Sync tracks from beatcloud to USB_PATH.
    * DOWNLOAD_XML: Sync IMPORT_USER's beatcloud XML to XML_PATH's parent
        folder.
    * UPLOAD_MUSIC: Sync tracks from USB_PATH to beatcloud.
    * UPLOAD_XML: Sync XML_PATH to USER's beatcloud XML folder.
"""
from datetime import datetime
import logging
import logging.config
import os
from traceback import format_exc

from djtools import (
    build_config,
    REKORDBOX_OPERATIONS,
    SPOTIFY_OPERATIONS,
    SYNC_OPERATIONS,
    upload_log,
    UTILS_OPERATIONS,
)


# Initialize logger.
log_file = os.path.join(
    os.path.dirname(__file__),
    "logs",
    f'{datetime.now().strftime("%Y-%m-%d")}.log',
).replace(os.sep, "/")
log_conf = os.path.join(
    os.path.dirname(__file__), "configs", "logging.conf"
).replace(os.sep, "/")
logging.config.fileConfig(
    fname=log_conf,
    defaults={"logfilename": log_file},
    disable_existing_loggers=False,
)
logger = logging.getLogger(__name__)

try:
    import Levenshtein
except ImportError:
    logger.warning(
        "NOTE: Track similarity can be made faster by running "
        '`pip install "dj-beatcloud[levenshtein]"`'
    )

# Load "config.yaml".
try:
    config = build_config()
    logger.setLevel(config["configs"].LOG_LEVEL)
except Exception as exc:
    msg = f"Failed to load config: {exc}"
    logger.critical(msg)
    raise ValueError(msg) from exc


def main():
    """This is the entry point for the DJ Tools library."""

    # Run "rekordbox", "spotify", "utils", and "sync" package operations if 
    # any of the flags to do so are present in the config.
    beatcloud_cache = []
    for package in [
        REKORDBOX_OPERATIONS,
        SPOTIFY_OPERATIONS,
        UTILS_OPERATIONS,
        SYNC_OPERATIONS,
    ]:
        for operation, func in package.items():
            pkg_name = func.__module__.split(".")[1]
            pkg_cfg = config.get(pkg_name)
            if not pkg_cfg:
                raise RuntimeError(
                    f"config doesn't have options for the '{pkg_name}' package"
                )
            if not getattr(pkg_cfg, operation):
                continue
            try:
                logger.info(f"Beginning {operation}...")
                if operation in ["CHECK_TRACKS", "DOWNLOAD_MUSIC"]:
                    beatcloud_cache = func(
                        pkg_cfg, beatcloud_tracks=beatcloud_cache
                    )
                else:
                    func(pkg_cfg)
            except Exception as exc:
                logger.error(f"{operation} failed: {exc}\n{format_exc()}")

    # Attempt uploading log file.
    upload_log(config["sync"], log_file)


if __name__ == "__main__":
    main()
