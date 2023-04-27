# Sync Files with the Beatcloud

In this guide you will learn how to sync audio and database files between your USB and the Beatcloud.

## Prerequisites
* [Setup object storage for syncing files](setup_object_storage.md)

## Why sync files with the Beatcloud?
Syncing your audio files gives you a reliable backup of your tracks and allows you share them with your DJ friends.

Syncing your database files also improves reliability since you may lose, damage, or corrupt your USB containing your database. Additionally, you may want to allow other users to import tracks using your tags, beatgrids, hot cues, etc. contained within that database file.

## How it's done

### Uploading music

1. Move new audio files to the desired location under `USB_PATH`
    * At the time of writing, this must be under `<USB_PATH>/DJ Music/`
    * It's *highly* recommended that the top-level folders under `DJ Music` are usernames so that the [create Spotify playlists from other users' uploads](spotify_playlist_from_upload.md) feature works as expected
    * It's also *highly* recommended that folders under `DJ Music` follow the convention `<username>/<broad genre>/<date>/` to improve the organization and usability of the Beatcloud
        * For example, I may decide I dislike Bob's taste in Techno so I would like the ability to configure the `DOWNLOAD_EXCLUDE_DIRS` option to be something like `["bob/Techno"]`
1. Run the command `djtools --upload-music`

### Downloading music
1. Run the command `djtools --download-music`

### Uploading XML
1. [Export](../conceptual_guides/rekordbox_collection.md#representations-of-your-collection) an up-to-date copy of your Rekordbox Collection
1. Ensure the `XML_PATH` option points to this file
1. Run the command `djtools --upload-xml`

### Downloading XML
1. Set the `IMPORT_USER` option to the username of another user in your Beatcloud
    - This username must exist as a key in `registered_users.yaml` (you'll have to manually update this file each time a new user runs `djtools` for the first time)
    - This username must exist as a directory in the Beatcloud under `dj.beatcloud.com/xml` (it will if `IMPORT_USER` has ever run `--upload-xml`)
1. Run the command `djtools --download-xml`
