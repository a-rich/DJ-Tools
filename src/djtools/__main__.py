"""This is the entry point for the DJ Tools library.

Collection operations:
    * COLLECTION_PLAYLISTS (collection.playlist_builder.py): Automatically
        create a playlist structure based on the tags present in a collection.
    * COPY_PLAYLISTS (copy_playlists.py): Copy audio files from
        playlists to a new location and generate a new collection with updated
        locations.
    * SHUFFLE_PLAYLISTS (shuffle_playlists.py): Set ID3 tags of tracks in
        playlists sequentially (after shuffling) to randomize.

Spotify operations:
    * SPOTIFY_PLAYLISTS (spotify.playlist_builder.py): Creating and updating
        Spotify playlists using subreddit top posts.
    * SPOTIFY_PLAYLISTS_FROM_UPLOAD (spotify.playlist_builder.py): Creating and
        updating Spotify playlists using the Discord webhook output from users
        uploading music.

Utils operations:
    * CHECK_TRACKS (check_tracks.py): Identify overlap between Spotify
        playlists and / or local directories and and the Beatcloud.
    * URL_DOWNLOAD (url_download.py): Download tracks from a URL (e.g.
        Soundcloud playlist).

Sync operations:
    * DOWNLOAD_MUSIC: Sync tracks from Beatcloud to USB_PATH.
    * DOWNLOAD_COLLECTION: Sync IMPORT_USER's collection to COLLECTION_PATH's
        parent folder.
    * DOWNLOAD_SPOTIFY_PLAYLIST: Sync tracks in a Spotify playlist from
        Beatcloud to USB_PATH.
    * UPLOAD_MUSIC: Sync tracks from USB_PATH to Beatcloud.
    * UPLOAD_COLLECTION: Sync COLLECTION_PATH to USER's collection folder.
"""

import logging

from djtools import main

try:
    import Levenshtein  # pylint: disable=unused-import
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning(
        "NOTE: Track similarity can be made faster by running "
        "`pip install python-Levenshtein"
    )


if __name__ == "__main__":
    main()
