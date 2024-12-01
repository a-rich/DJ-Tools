# Overview
DJ Tools is a Python library with many features for streamlining the processes around collecting, curating, and sharing a music collection. Users of the library may have different needs and, therefore, only require some of the features provided. Let's briefly go over what DJ Tools offers so you can determine what's relevant to you.

If you want to learn more about how to use DJ Tools to achieve any of the following, please visit the [How-to Guides](../../how_to_guides/index.md).

## Collection
This package reads and writes a collection of tracks and playlists. Operations can be performed on this collection such as shuffling and creating backups of playlists and the files that they're comprised of.

Perhaps the most useful feature in the `collection` package is the playlist builder.
The playlist builder automatically builds playlists using the metadata associated with tracks in your collection and a `collection_playlists.yaml` configuration file.

The `tags` key in your `collection_playlists.yaml` specifies a desired playlist structure using singular tags (genre tags and "other" tags).
The `combiner` key specifies playlists using powerful [boolean algebra expressions](https://en.wikipedia.org/wiki/Set_theory#Basic_concepts_and_notation) that apply operations on a variety of operands including, but not limited to: tags, playlists, BPM, rating, release year, date added, comments, artists, labels, etc.

For more information on the playlist builder, see the How-to Guides for [tag](../../how_to_guides/collection_playlists.md) and [combiner](../../how_to_guides/combiner_playlists.md) playlists.

## Spotify
This package uses the Spotify and Reddit APIs to automatically generate playlists from Reddit submissions and the uploads of other users of your Beatcloud instance.

By configuring particular subreddits, you can ensure that you're getting a steady stream of focused music discovery that caters to your interests.

Being able to generate Spotify playlists from other users' uploads gives you an opportunity to preview tracks before you decide whether or not you want to sync them (and it goes hand-in-hand with a sister feature of the `sync` package that makes it easy to sync tracks from this playlist).

## Sync
This package is essentially a wrapper around an AWS S3 API compliant object storage solution. Throughout the code and documentation, this cloud storage instance is referred to as the "Beatcloud".

The core of the `sync` package is the music uploading and downloading features that the progenitor version of DJ Tools was constructed for. This lets you backup your collection for safe keeping and, furthermore, allows you to share your collection amongst your DJ friends. It also can be used to upload your DJ platform's database as well as download databases that other users have uploaded.

If you're downloading another user's database, this package will doctor it so the track locations point to where they exist for you (assuming you're all syncing with the same Beatcloud instance). This allows you to import tracks from another user's collection inheriting all their tags, hot cues, etc.

As mentioned under the [Spotify](#spotify) section above, the `sync` package offers a sister feature for syncing just the tracks that appear in a playlist generated from another user's upload. This allows you to (a) preview and filter the tracks another user uploads in Spotify and (b) automatically format the `download_exclude_dirs` configuration option on-the-fly based on the remaining tracks of the playlist.

## Utils
The `utils` package has the following miscellaneous features:

-  `check_tracks` which will compare the filenames of tracks in the Beatcloud with both / either tracks in `check_tracks_spotify_playlists` and / or filenames globbed from `local_dirs`. This is very useful for predetermining if you're about to sync duplicate tracks to the Beatcloud.
- `normalize_audio` which will transform the files globbed from `local_dirs` such that their peak amplitude leaves `audio_headroom` and exports them in `audio_format` at `audio_bitrate`. This is very useful for ensuring all the tracks you add to the Beatcloud are standardized; say `320k` `mp3` files with a peak amplitude of `0.0` decibels.
- `process_recording`: given a recording file and Spotify playlist, chunk the recording into individual tracks, name the files, and export with tags using data from the Spotify API. Tracks are normalized with `audio_headroom` and exported in `audio_format` at `audio_bitrate`.
- `url_download` which is a simple wrapper around the [youtube-dl](https://github.com/ytdl-org/youtube-dl) package for extracting audio files from URLs.
