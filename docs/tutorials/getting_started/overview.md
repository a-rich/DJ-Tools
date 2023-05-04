# Overview
DJ Tools is a Python library with many features for streamlining the processes around collecting, curating, and sharing a music collection. Users of the library may have different needs and, therefore, only require some of the features provided. Let's briefly go over what DJ Tools offers so you can determine what's relevant to you.

If you want to learn more about how to use DJ Tools to achieve any of the following, please visit the [How-to Guides](../../how_to_guides/index.md).

## Rekordbox
This package, as the name suggests, performs operations that are only relevant to Rekordbox users. In general, this package manipulates an exported XML of your Rekordbox Collection in order to add functionality that's lacking in the Rekordbox software.

For example, you can shuffle playlists and create backups of playlists and the files that they're comprised of.

My favorite feature in the `rekordbox` package automatically builds playlists based on tags in your collection and allows you to express powerful [boolean algebra expressions](https://en.wikipedia.org/wiki/Set_theory#Basic_concepts_and_notation) that combine and filter playlists.

## Spotify
This package interfaces with the Spotify (and Reddit) API in order to automatically generate playlists from Reddit submission and the uploads of other users of your Beatcloud instance.

By configuring particular subreddits, you can ensure that you're getting a steady stream of focused music discovery that caters to your interests.

Being able to generate Spotify playlists from other users' uploads gives you an opportunity to preview tracks before you decide whether or not you want to sync them (and it goes hand-in-hand with a sister feature of the `sync` package that makes it easy to sync tracks from this playlist).

## Sync
This package is essentially a wrapper around an AWS S3 API compliant object storage solution. Throughout the code and documentation, this cloud storage instance is referred to as the "Beatcloud".

The core of the `sync` package is the music uploading and downloading features that the progenitor version of DJ Tools was constructed for. This lets you backup your collection for safe keeping and, furthermore, allows you to share your collection amongst your DJ friends. It also can be used to upload your XML database export as well as download XMLs that other users have uploaded.

If you're downloading another user's XML, this package will doctor the file so the track locations point to where they exist for you (assuming you're all syncing with the same Beatcloud instance). This allows you to import tracks from another user's Collection inheriting all their tags, hot cues, etc.

As mentioned under the [Spotify](#spotify) section above, the `sync` package offers a sister feature for syncing just the tracks that appear in a playlist generated from another user's upload. This allows you to (a) preview and filter the tracks another user uploads in Spotify and (b) automatically format the `DOWNLOAD_EXCLUDE_DIRS` configuration option on-the-fly based on the remaining tracks of the playlist.

## Utils
This package contains utilities that either don't fit into any of the other packages or are otherwise used by multiple packages.

The primary utility offered by this package checks the contents of your Beatcloud instance and compares the filenames with either/both tracks in one or more Spotify playlists and files in one or more local directories.

This is very useful for predetermining if you're about to sync duplicate tracks to the Beatcloud.

The `utils` package also offers a simple wrapper around the [youtube-dl](https://github.com/ytdl-org/youtube-dl) package for extracting audio files from URLs.
