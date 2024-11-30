"""This is the entry point for the DJ Tools library.

Collection operations:
    * collection_playlists (collection.playlist_builder.py): Automatically
        create a playlist structure based on the tags present in a collection.
    * copy_playlists (copy_playlists.py): Copy audio files from
        playlists to a new location and generate a new collection with updated
        locations.
    * shuffle_playlists (shuffle_playlists.py): Set ID3 tags of tracks in
        playlists sequentially (after shuffling) to randomize.

Spotify operations:
    * spotify_playlists (spotify.playlist_builder.py): Creating and updating
        Spotify playlists using subreddit top posts.
    * spotify_playlists_from_upload (spotify.playlist_builder.py): Creating and
        updating Spotify playlists using the Discord webhook output from users
        uploading music.

Utils operations:
    * check_tracks (check_tracks.py): Identify overlap between Spotify
        playlists and / or local directories and and the Beatcloud.
    * url_download (url_download.py): Download tracks from a URL (e.g.
        Soundcloud playlist).

Sync operations:
    * download_music: Sync tracks from Beatcloud to usb_path.
    * download_collection: Sync import_user's collection to collection_path's
        parent folder.
    * download_spotify_playlist: Sync tracks in a Spotify playlist from
        Beatcloud to usb_path.
    * upload_music: Sync tracks from usb_path to Beatcloud.
    * upload_collection: Sync collection_path to user's collection folder.
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
