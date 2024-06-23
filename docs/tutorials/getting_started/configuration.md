# Configuration
When the `djtools` command is run, `build_config` looks for a `config.yaml` in the package's `config` directory and creates a `BaseConfig` object using its values. 
If `djtools` was run with any CLI options, those values override whatever was set in the `BaseConfig` using the values in `config.yaml`.

If `config.yaml` doesn't exist, it will be generated when running `djtools`.
If `config.yaml`, or any of the values it might contain, is missing then the default values in the Python object are used instead.
If `config.yaml` contains any unsupported options, `djtools` will fail as extra keys are forbidden.

## [Base config][djtools.configs.config.BaseConfig]
* `ARTIST_FIRST`: used to indicate that your Beatcloud tracks adhere to the `Artist1, Artist2 - Title (Artist2 Remix)` format rather than the `Title (Artist2 Remix) - Artist1, Artist2` format expected by default 
* `LOG_LEVEL`: logger log level
* `VERBOSITY`: verbosity level for logging messages

## [Collection config][djtools.collection.config.CollectionConfig]
* `COLLECTION_PATH`: the full path to your collection...the parent directory where this points to is also where all other collections generated or utilized by this library will exist
* `COLLECTION_PLAYLISTS`: boolean flag to trigger the generation of a playlist structure (as informed by `collection_playlists.yaml`) using the tags in `COLLECTION_PATH`...the resulting collection is the file at `COLLECTION_PATH`
* `COLLECTION_PLAYLISTS_REMAINDER`: whether tracks of remainder tags (those not specified in `collection_playlists.yaml`) will be placed in a `folder` called "Unused Tags" with individual tag playlists or a `playlist` called "Unused Tags"
* `COLLECTION_PLAYLIST_FILTERS`: list of `PlaylistFilter` classes used to apply special filtering logic to tag playlists
* `COPY_PLAYLISTS`: list of playlists in `COLLECTION_PATH` to (a) have audio files copied and (b) have track data written to a new collection with updated locations
* `COPY_PLAYLISTS_DESTINATION`: path to copy audio files to
* `PLATFORM`: DJ platform used (e.g. `rekordbox`)
* `SHUFFLE_PLAYLISTS`: list of playlists that will have their tracks shuffled

## [Spotify config][djtools.spotify.config.SpotifyConfig]
* `REDDIT_CLIENT_ID`: client ID for registered Reddit API application
* `REDDIT_CLIENT_SECRET`: client secret for registered Reddit API application
* `REDDIT_USER_AGENT`: user-agent for registered Reddit API application
* `SPOTIFY_CLIENT_ID`: client ID for registered Spotify API application
* `SPOTIFY_CLIENT_SECRET`: client secret for registered Spotify API application
* `SPOTIFY_PLAYLISTS`: boolean flag to trigger the automatic generation or updating of Spotify playlists from subreddits
* `SPOTIFY_PLAYLIST_DEFAULT_LIMIT`: default number of tracks for a Spotify playlist
* `SPOTIFY_PLAYLIST_DEFAULT_PERIOD`: default subreddit period for a Spotify playlist
* `SPOTIFY_PLAYLIST_DEFAULT_TYPE`: default subreddit filter type for a Spotify playlist
* `SPOTIFY_PLAYLIST_FROM_UPLOAD`: boolean flag to trigger automatic generation of updating of a Spotify playlist from the Discord webhook output of a user's music upload (output must be copied to the system clipboard)
* `SPOTIFY_PLAYLIST_FUZZ_RATIO`: the minimum Levenshtein similarity between a Spotify API track search result and a subreddit post title (if post is not directly a Spotify URL) to trigger the addition of that track to the corresponding Spotify auto-playlist
* `SPOTIFY_PLAYLIST_POST_LIMIT`: the maximum number of posts to retrieve from a subreddit
* `SPOTIFY_PLAYLIST_SUBREDDITS`: list of `SubredditConfig` objects from which tracks should be added to Spotify auto-playlist; each element is a dictionary with keys for a subreddit's "name", "type", "period", and "limit"
* `SPOTIFY_REDIRECT_URI`: redirect URI for registered Spotify API application
* `SPOTIFY_USERNAME`: Spotify username that will keep playlists automatically generated

## [Sync config][djtools.sync.config.SyncConfig]
* `AWS_PROFILE`: the name of the profile used when running `aws configure --profile`
* `AWS_USE_DATE_MODIFIED`: up/download files that already exist at the destination if the date modified field at the source is after that of the destination...BE SURE THAT ALL USERS OF YOUR `BEATCLOUD` INSTANCE ARE ON BOARD BEFORE UPLOADING WITH THIS FLAG SET!
* `BUCKET_URL`: URL for an AWS S3 API compliant storage location
* `DISCORD_URL`: webhook URL for messaging a Discord server's channel when new music has been uploaded to the `beatcloud`
* `DOWNLOAD_COLLECTION`: sync the collection of `IMPORT_USER` from the `beatcloud` to the directory that `COLLECTION_PATH` is in
* `DOWNLOAD_EXCLUDE_DIRS`: the list of paths (relative to the `DJ Music` folder on your `USB_PATH`) that should NOT be downloaded from the `beatcloud` when running the `download_music` sync operation
* `DOWNLOAD_INCLUDE_DIRS`: the list of paths (relative to the `DJ Music` folder on your `USB_PATH`) that should exclusively be downloaded from the `beatcloud` when running the `download_music` sync operation
* `DOWNLOAD_MUSIC`: sync beatcloud to "DJ Music" folder
* `DOWNLOAD_SPOTIFY_PLAYLIST`: if this is set to the name of a playlist (present in `spotify_playlists.yaml`), then only the Beatcloud tracks present in this playlist will be downloaded
* `DRYRUN`: show `aws s3 sync` command output without running
* `IMPORT_USER`: the username of a fellow `beatcloud` user whose collection you want to download
* `UPLOAD_COLLECTION`: sync `COLLECTION_PATH` to the beatcloud
* `UPLOAD_EXCLUDE_DIRS`: the list of paths (relative to the `DJ Music` folder on your `USB_PATH`) that should NOT be uploaded to the `beatcloud` when running the `upload_music` sync operation
* `UPLOAD_INCLUDE_DIRS`: the list of paths (relative to the `DJ Music` folder on your `USB_PATH`) that should exclusively be uploaded to the `beatcloud` when running the `upload_music` sync operation
* `UPLOAD_MUSIC`: sync "DJ Music" folder to the beatcloud
* `USB_PATH`: the full path to the USB drive which contains all your music files
* `USER`: this is the username of the current user...if left as an empty string, then your operating system username will be used...it's recommended that you only override this if your username changes from what other users of your `beatcloud` instance are expecting (to ensure consistency...i.e. when you get a new computer with a different username)

## [Utils config][djtools.utils.config.UtilsConfig]
* `AUDIO_BITRATE`: string representing the integer in the range [`36`, `320`] for the bitrate to write audio at e.g. `"320"`
* `AUDIO_DESTINATION`: path to where downloaded and / or exported files go to
* `AUDIO_FORMAT`: string representing the file format write audio in e.g. `"mp3"`
* `AUDIO_HEADROOM`: non-negative float representing the amount of headroom in decibels to leave when normalizing audio
* `CHECK_TRACKS`: boolean flag to trigger checking the contents of the `beatcloud` (to identify redundancies)
* `CHECK_TRACKS_FUZZ_RATIO`: the minimum Levenshtein similarity for indicating potential redundancies between Spotify playlists / local directories and the `beatcloud`
* `CHECK_TRACKS_SPOTIFY_PLAYLISTS`: list of Spotify playlists to use with `CHECK_TRACKS` (must exist in `spotify_playlists.yaml`)
* `LOCAL_DIRS`: list of local directories to use with `CHECK_TRACKS`
* `NORMALIZE_AUDIO`: boolean flag to trigger normalizing audio files at `LOCAL_DIRS`,
* `PROCESS_RECORDING`: boolean flag to trigger processing an audio recording using a Spotify playlist
* `RECORDING_FILE`: Audio recording to pair with `RECORDING_PLAYLIST`
* `RECORDING_PLAYLIST`: Spotify playlist to pair with `RECORDING_FILE`
* `TRIM_INITIAL_SILENCE`: Milliseconds of initial silence to trim off `RECORDING_FILE`. Can also be a negative integer to prepend silence. Can also be "auto" or "smart" for automatic silence detection or a home-brewed algorithm for finding the optimal offset.
* `URL_DOWNLOAD`: URL from which music files should be downloaded (i.e. a Soundcloud playlist)
