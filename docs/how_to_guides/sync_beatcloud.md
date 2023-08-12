# Sync Files with the Beatcloud

In this guide you will learn how to sync audio and database files with the Beatcloud.

## Prerequisites

* [Setup object storage for syncing files](setup_object_storage.md)
* [Configure the `sync` options](../tutorials/getting_started/configuration.md#sync-config)

## Why sync files with the Beatcloud?
Syncing your audio files gives you a reliable backup of your tracks and allows you share them with your DJ friends.

Syncing your database files also improves reliability since you may lose, damage, or corrupt your database. Additionally, you may want to allow other users to import tracks using your tags, beatgrids, hot cues, etc. contained within that database file.

## How it's done

`Note`: if you want to first preview which files will be uploaded or downloaded by the `--upload-music` or `--download-music` commands, you can append the flag `--dryrun`.

### Uploading music

1. Move new audio files to the desired location under `<USB_PATH>/DJ Music/`
    * Note that _it is required_ that you put all your music files under this path
    * It's *highly* recommended that the top-level folders under `DJ Music` are usernames so that the [Create Spotify playlists from other users' uploads](spotify_playlist_from_upload.md) feature works as expected
    * It's also *highly* recommended that folders under `DJ Music` follow the convention `<username>/<broad genre>/<date>/` to improve the organization and usability of the Beatcloud; for example:
        * I may decide I dislike Bob's taste in Techno so I would configure the `DOWNLOAD_EXCLUDE_DIRS` option to be `["bob/Techno"]`
        * I may decide I only want all of Sally's music and Bob's music uploaded on `2023-04-04` so I would configure the `DOWNLOAD_INCLUDE_DIRS` option to be `["sally", "bob/*/2023-04-04"]`
        * As you can see, having a structured music collection gives users a high degree of flexibility when it comes to syncing others' tracks; it also pairs well with other features like [Create Spotify Playlists From Other Users' Uploads](spotify_playlist_from_upload.md) and [Sync Tracks From Spotify Playlists](sync_spotify.md)
1. Configure `UPLOAD_INCLUDE_DIRS` or `UPLOAD_EXCLUDE_DIRS` (only one may be specified at a time) to include or exclude specific paths
1. [Optional] If you want to notify a Discord server of your uploaded files, make sure you first [setup a Discord webhook](../tutorials/getting_started/setup.md#discord-webhook)
    - This is required for the [Create Spotify playlists from other users' uploads](spotify_playlist_from_upload.md) feature to work
1. Run the command `djtools --upload-music`

### Downloading music
1. The same points above about including and excluding paths apply to `DOWNLOAD_INCLUDE_DIRS` and `DOWNLOAD_EXCLUDE_DIRS`.
1. Run the command `djtools --download-music`

### Uploading collection
1. Export an up-to-date copy of your collection (e.g. [create a Rekordbox XML](../conceptual_guides/rekordbox_collection.md#representations-of-your-collection))
1. Ensure the `COLLECTION_PATH` option points to this collection
1. Run the command `djtools --upload-collection`

### Downloading collection
1. Set the `IMPORT_USER` option to the username of another user in your Beatcloud
    - This username must exist as a directory in the Beatcloud under `dj.beatcloud.com/collections` (it will if this user has ever run `--upload-collection`)
1. Run the command `djtools --download-collection`

`Note`: you can set `IMPORT_USER` to your own `USER` value to retrieve a backup of your collection.
