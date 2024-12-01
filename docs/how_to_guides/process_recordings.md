# Process Recorded Files Using Spotify Playlists

In this guide you will learn how to automate splitting a recorded file into individual tracks using a Spotify playlist. These tracks will be normalized and exported with a configured bitrate and file format with tags pre-populated.

## Prerequisites

* [Installing FFmpeg](../tutorials/getting_started/setup.md#FFmpeg)

## Why process recorded files

Manually splitting a recorded audio file into individual tracks is both time consuming and error prone. Users may forget to apply amplitude normalization or mistype the filenames which are inputs to downstream processes like extracting title and artist tags. Users may also forget to export files with an acceptable file format or bit rate which can degrade the quality of your collection.

## How it's done

1. Configure `recording_file` to point to your recorded audio file
1. Configure `recording_playlist` to a valid Spotify playlist name present in your `spotify_playlists.yaml`
1. Configure `audio_bitrate`, `audio_format`, and `audio_headroom` to the desired values (defaults are `320k`, `mp3`, and `0.0` respectively)
1. Configure `audio_destination` to point to where you want the files to export to
1. Run the command `--process-recording`
