"""This is the entry point for the DJ Tools library.

Rekordbox operations:
    * COPY_PLAYLISTS (copy_playlists.py): Copy audio files from
        playlists to a new location and generate a new XML with updated
        Location fields.
    * RANDOMIZE_PLAYLISTS (randomize_playlists.py): Set ID3 tags of tracks in
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
    * URL_DOWNLOAD (url_download.py): Download tracks from a URL (e.g. Soundcloud
        playlist).

Sync operations:
    * DOWNLOAD_MUSIC: Sync tracks from beatcloud to USB_PATH.
    * DOWNLOAD_XML: Sync IMPORT_USER's beatcloud XML to XML_PATH's parent
        folder.
    * UPLOAD_MUSIC: Sync tracks from USB_PATH to beatcloud.
    * UPLOAD_XML: Sync XML_PATH to USER's beatcloud XML folder.
"""

import logging

from djtools.main import main

try:
    import Levenshtein
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning(
        "NOTE: Track similarity can be made faster by running "
        '`pip install python-Levenshtein'
    )


if __name__ == "__main__":
    main()
