# Overview
DJ Tools is a Python library with many features for streamlining the processes around collecting, curating, and sharing a music collection. Users of the library may have different needs and, therefore, only require some of the features provided. Let's briefly go over the distinct sets of features so you can determine which features of DJ Tools are relevant to you.

If you want to learn more about how to use DJ Tools to achieve any of the following, please visit the [How-to Guides](../how_to_guides/index.md).

## Rekordbox
This package, as the name suggests, performs operations that are, at the time of writing, only relevant to Rekordbox users. In general, this package manipulates an exported XML of your Rekordbox Collection in order to add functionality that's lacking in the Rekordbox software. The current set of supplementary functionality includes:

1. [Shuffling][djtools.rekordbox.shuffle_playlists.shuffle_playlists] playlists by overwriting the contents of tracks' `Track Number` tag
1. [Copying files][djtools.rekordbox.copy_playlists.copy_playlists] for the tracks of playlists to a new destination and generating an XML that points these tracks to said destination (for, as examples, creating a backup USB or sharing a USB with another DJ)
1. [Building playlists][djtools.rekordbox.playlist_builder.build_playlists] from data stored in tags (Genre, My Tags, etc.)

## Spotify
This package interfaces with the Spotify API in order to automatically generate playlists. The two features provided from this package are:

1. [Pulling submissions from subreddits][djtools.spotify.playlist_builder.update_auto_playlists] via the Reddit API and finding Spotify tracks that match the titles of the submissions
1. [Searching Spotify][djtools.spotify.playlist_builder.playlist_from_upload] for tracks in the [webhook][djtools.sync.helpers.webhook] output from a users' run of [upload_music][djtools.sync.sync_operations.upload_music] 

## Sync
This package is essentially a wrapper around an AWS S3 API compliant object storage solution. Throughout the code and documentation, this cloud storage instance is referred to as the "Beatcloud". The sync pacakge can be used to:

1. [Sync files with the Beatcloud](../../how_to_guides/sync_beatcloud.md)

If you're downloading another user's XML, [this function][djtools.sync.helpers.rewrite_xml] is called to perform a search & replace on the `Location` fields in the XML, updating them so they point to the files on your USB instead of where they exist on the other user's USB. This allows you to import tracks from another user's Collection inheriting all their tags, hot cues, etc.

Additionally, the `download_music` command can also be run with the `--download-spotify <name of playlist>` flag which is intended to be a sister command to [playlist_from_upload][djtools.spotify.playlist_builder.playlist_from_upload]. This allows you to sync just the tracks you want from another user's upload without having to format a potentially lengthy argument to the `DOWNLOAD_INCLUDE_DIRS` option.

## Utils
This package contains utilities that either don't fit into any of the other packages or are otherwise used by multiple packages. The two features provided from this package are:

1. [Comparing tracks][djtools.utils.check_tracks.compare_tracks] in a set of Spotify playlists and/or local directories with the contents of the Beatcloud to identify redundancies
1. [Extract audio][djtools.utils.url_download.url_download] from a URL
