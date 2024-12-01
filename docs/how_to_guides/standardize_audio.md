# Standardize Audio Files

In this guid you will learn how to standardize audio files prior to uploading them to the Beatcloud.

## Prerequisites

* [Installing FFmpeg](../tutorials/getting_started/setup.md#FFmpeg)

## Why standardize audio files?
Users may want to keep their Beatcloud footprint smaller by formatting all their tracks as mp3 files while also ensuring the quality of their audio files is top-notch (see the [file standardization conceptual guide](../conceptual_guides/file_standardization.md#audio-file-format)).

Users may also want to normalize their audio files' peak amplitude to some target headroom so that they don't have to worry about adjusting the gain while mixing.

## How it's done

1. Configure the directory or directories containing your audio files with `local_dirs`
1. Configure `audio_bitrate`, `audio_format`, and `audio_headroom` to the desired values (defaults are `320k`, `mp3`, and `0.0` respectively)
1. Run the command `--normalize-audio`
