# Utils

## Contents
* Overview
* Setup
* Usage

# Overview
The `utils` package contains modules:
* `copy_playlists_tracks`: copies audio files for tracks within a set of playlists to a new location and writes a new XML with these updated paths
* `helpers`: functions like:
  - uploading logs
  - getting a list of tracks in the Beatcloud
  - getting a list of local files in one or more directories
  - comparing Spotify and local files with the Beatcloud to identify overlap
* `youtube_dl`: downloads files from a URL

# Setup
The `youtube_dl` module requires that `YOUTUBE_DL_URL` is a valid URL from which audio files can be downloaded.

The `copy_playlists_tracks` module requires that the playlists in `COPY_PLAYLISTS_TRACKS` exist inside `XML_PATH`, and `COPY_PLAYLISTS_TRACKS_DESTINATION` is set to a valid path.

The `helpers` module contains many operations touching the various subpackages of this library. Many different configuration options are required to use the full set of features.

# Usage
## copy_playlists_tracks
To trigger the `copy_playlists_tracks` module, set `COPY_PLAYLISTS_TRACKS` to one or more valid playlists in `XML_PATH` and ensure `COPY_PLAYLISTS_TRACKS` is set.
## check_track_overlap
To compare the contents of Spotify playlists and / or local directories with the contents of the Beatcloud, set `SPOTIFY_CHECK_PLAYLISTS` to one or more playlists names that exists in your `spotify_playlists.json`; to include local directories, set `LOCAL_CHECK_DIRS` to one or more paths to recursively glob files from. The option `CHECK_TRACK_OVERLAP_FUZZ_RATIO` is used to control the similarity threshold for matching.
## youtube_dl
To trigger the `youtube_dl` module, set `YOUTUBE_DL: true`. IF `YOUTUBE_DL_LOCATION` is not set, tracks will be downloaded to the current directory. Once tracks are downloaded, make sure all file names adhere to convention:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Title (Artist2 Remix) - Artist1, Artist2.mp3`

After tracks are downloaded, you can follow the prescribed workflows specified under the main README's "Basic Information" section to ensure consistency both in your local library and in the `beatcloud`.

