# Utils

## Contents
* Overview
* Setup
* Usage

# Overview
The `utils` package contains modules:
* `check_tracks`: compares Spotify and / or local files with the Beatcloud to identify overlap
* `youtube_dl`: downloads files from a URL

# Setup
The `CHECK_TRACKS` requires either / both:
 * `CHECK_TRACKS_SPOTIFY_PLAYLISTS` to be set to a list of Spotify playlists that appear in `spotify_playlists.yaml`
 * `CHECK_TRACKS_LOCAL_DIRS` to be set to the list of local directories to search

 If using the `CHECK_TRACKS_SPOTIFY_PLAYLISTS` option, you must populate the `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and `SPOTIFY_REDIRECT_URI` configuration options.

 In either case, you will need to have `AWS_PROFILE` set to a valid AWS profile configured with the `awscli` command-line tool.

Using `YOUTUBE_DL_URL` requires that `YOUTUBE_DL_URL` is a valid URL from which audio files can be downloaded. `YOUTUBE_DL_LOCATION` can be set to control where files are downloaded to. If not set, they'll be downloaded to the current directory.

# Usage
## check_tracks
To compare the contents of Spotify playlists with the contents of the Beatcloud, set `CHECK_TRACKS_SPOTIFY_PLAYLISTS` to one or more playlists names that exists in your `spotify_playlists.yaml`; to compare files in local directories with the contents of the Beatcloud, set `CHECK_TRACKS_LOCAL_DIRS` to one or more paths to recursively glob files from. The option `CHECK_TRACKS_FUZZ_RATIO` is used to control the similarity threshold for matching.
## youtube_dl
To trigger the `youtube_dl` module, set `YOUTUBE_DL_URL` to a valid URL. If `YOUTUBE_DL_LOCATION` is not set, tracks will be downloaded to the current directory. Once tracks are downloaded, make sure all file names adhere to convention:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Title (Artist2 Remix) - Artist1, Artist2.mp3`

After tracks are downloaded, you can follow the prescribed workflows specified under the main README's "Basic Information" section to ensure consistency both in your local library and in the Beatcloud.
