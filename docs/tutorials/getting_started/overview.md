# Overview
DJ Tools is a Python library with many features for streamlining the processes around collecting, curating, and sharing a music collection. Users of the library may have different needs and, therefore, only require some of the features provided. Let's briefly go over what DJ Tools offers so you can determine what's relevant to you.

If you want to learn more about how to use DJ Tools to achieve any of the following, please visit the [How-to Guides](../../how_to_guides/index.md).

## Collection
This package reads and writes a collection of tracks and playlists. Operations can be performed on this collection such as shuffling and creating backups of playlists and the files that they're comprised of.

Perhaps the most useful features in the `collection` package:

1. automatically build playlists based on your tags and a desired folder structure 
1. allow you to define playlists using powerful [boolean algebra expressions](https://en.wikipedia.org/wiki/Set_theory#Basic_concepts_and_notation) that combine and filter playlists

With this latter feature, you can create, for example, a playlist that has all your `Dark` tracks that are also in the set of tracks that are either `Dubstep`, in the BPM range `138` to `142`, or have `Eprom` somewhere in the artist field, but don't come from a playlist called `Weak Beats`:

`Dark & (Dubstep | [138-142] | {artist: *Eprom*}) ~ {playlist: Weak Beats}`

## Spotify
This package uses the Spotify and Reddit APIs to automatically generate playlists from Reddit submission and the uploads of other users of your Beatcloud instance.

By configuring particular subreddits, you can ensure that you're getting a steady stream of focused music discovery that caters to your interests.

Being able to generate Spotify playlists from other users' uploads gives you an opportunity to preview tracks before you decide whether or not you want to sync them (and it goes hand-in-hand with a sister feature of the `sync` package that makes it easy to sync tracks from this playlist).

## Sync
This package is essentially a wrapper around an AWS S3 API compliant object storage solution. Throughout the code and documentation, this cloud storage instance is referred to as the "Beatcloud".

The core of the `sync` package is the music uploading and downloading features that the progenitor version of DJ Tools was constructed for. This lets you backup your collection for safe keeping and, furthermore, allows you to share your collection amongst your DJ friends. It also can be used to upload your DJ platform's database as well as download databases that other users have uploaded.

If you're downloading another user's database, this package will doctor it so the track locations point to where they exist for you (assuming you're all syncing with the same Beatcloud instance). This allows you to import tracks from another user's collection inheriting all their tags, hot cues, etc.

As mentioned under the [Spotify](#spotify) section above, the `sync` package offers a sister feature for syncing just the tracks that appear in a playlist generated from another user's upload. This allows you to (a) preview and filter the tracks another user uploads in Spotify and (b) automatically format the `DOWNLOAD_EXCLUDE_DIRS` configuration option on-the-fly based on the remaining tracks of the playlist.

## Utils
The `utils` package has the following miscellaneous features:

-  `CHECK_TRACKS` which will compare the filenames of tracks in the Beatcloud with both / either tracks in `CHECK_TRACKS_SPOTIFY_PLAYLISTS` and / or filenames globbed from `LOCAL_DIRS`. This is very useful for predetermining if you're about to sync duplicate tracks to the Beatcloud.
- `NORMALIZE_AUDIO` which will transform the files globbed from `LOCAL_DIRS` such that their peak amplitude leaves `AUDIO_HEADROOM` and exports them in `AUDIO_FORMAT` at `AUDIO_BITRATE`. This is very useful for ensuring all the tracks you add to the Beatcloud are standardized; say `320k` `mp3` files with a peak amplitude of `0.0` decibels.
- `PROCESS_RECORDING`: given a recording file and Spotify playlist, chunk the recording into individual tracks, name the files, and export with tags using data from the Spotify API. Tracks are normalized with `AUDIO_HEADROOM` and exported in `AUDIO_FORMAT` at `AUDIO_BITRATE`.
- `URL_DOWNLOAD` which is a simple wrapper around the [youtube-dl](https://github.com/ytdl-org/youtube-dl) package for extracting audio files from URLs.
