"""This is the entry point for the DJ Tools library.

Rekordbox operations:
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
    * CHECK_TRACK_OVERLAP (check_track_overlap.py): Identify overlap between
        Spotify playlists and / or local directories and and the Beatcloud.
    * COPY_PLAYLISTS_TRACKS (copy_playlists_tracks.py): Copy audio files from
        playlists to a new location and generate a new XML with updated
        Location fields.
    * YOUTUBE_DL (youtube_dl.py): Download tracks from a URL (e.g. Soundcloud
        playlist).

Sync operations:
    * DOWNLOAD_MUSIC: Sync tracks from beatcloud to USB_PATH.
    * DOWNLOAD_XML: Sync XML_IMPORT_USER's beatcloud XML to
        XML_PATH's parent folder.
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

# Load "config.json", override with any command-line arguments, and
# validate the final config.
try:
    config = build_config()
    if config.get("LOG_LEVEL"):
        logger.setLevel(config["LOG_LEVEL"])
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
            if not config.get(operation):
                continue
            try:
                logger.info(f"Beginning {operation}...")
                if operation == "CHECK_TRACK_OVERLAP" or "DOWNLOAD_MUSIC":
                    beatcloud_cache = func(
                        config, beatcloud_tracks=beatcloud_cache
                    )
                else:
                    func(config)
            except Exception as exc:
                logger.error(f"{operation} failed: {exc}\n{format_exc()}")

    # Attempt uploading today's log file.
    upload_log(config, log_file)


if __name__ == "__main__":
    main()
