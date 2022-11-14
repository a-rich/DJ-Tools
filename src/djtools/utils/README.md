# Utils

## Contents
* Overview
* Setup
* Usage

# Overview
The `utils` package contains modules:
* `local_dirs_checker`: checks local tracks for overlap with those already in the beatcloud
* `youtube_dl`: downloads files from a URL to `DJ Music` -> `New Music`
* `helpers`: helper functions for top-level operations (`upload_log`)

# Setup
The `local_dirs_checker` module requires that both `USB_PATH` exists and the directories listed in `LOCAL_CHECK_DIRS` exist under the "DJ Music" folder of `USB_PATH`.

The `youtube_dl` module requires that `USB_PATH` exists and that `YOUTUBE_DL_URL` is a valid URL from which MP3 files can be downloaded.

# Usage

## local_dirs_checker
To trigger the `local_dirs_checker` module, set `CHECK_TRACK_OVERLAP: true` and populate `lOCAL_CHECK_DIRS` with directories under the "DJ Music" directory.

## youtube_dl
To trigger the `youtube_dl` module, set `YOUTUBE_DL: true`. Once tracks are downloaded, make sure all file names adhere to convention:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Title (Artist2 Remix) - Artist1, Artist2.mp3`

After tracks are downloaded, you can follow the prescribed workflows specified under the main README's "Basic Information" section to ensure consistency both in your local library and in the `beatcloud`.
