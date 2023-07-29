# Process Recorded Files Using Spotify Playlists

In this guide you will learn how to automate splitting a recorded file into individual tracks using a Spotify playlist. These tracks will be normalized and exported with a configured bitrate and file format with tags pre-populated.

## Prerequisites

* [Installing FFmpeg](../tutorials/getting_started/setup.md#FFmpeg)

## Why process recorded files

Manually splitting a recorded audio file into individual tracks is both time consuming and error prone. Users may forget to apply amplitude normalization or mistype the filenames which are inputs to downstream processes like extracting title and artist tags.

## How it's done

1. Ensure your `USB_PATH` is configured and available as the exported files are placed in `<USB_PATH>/DJ Music/New Music/`
1. Configure `RECORDING_FILE` to point to your recorded audio file
1. Configure `RECORDING_PLAYLIST` to a valid Spotify playlist name present in your `spotify_playlists.yaml`
1. Run the command `--process-recording`
