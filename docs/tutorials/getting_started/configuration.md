# Configuration
When the `djtools` command is run, `build_config` looks for a `config.yaml` in the package's `config` directory and creates a `BaseConfig` object using its values. 
If `djtools` was run with any CLI options, those values override whatever was set in the `BaseConfig` using the values in `config.yaml`.

If `config.yaml` doesn't exist, it will be generated when running `djtools`.
If `config.yaml`, or any of the values it might contain, is missing then the default values in the Python object are used instead.
If `config.yaml` contains any unsupported options, `djtools` will fail as extra keys are forbidden.

## [Base config][djtools.configs.config.BaseConfig]
* `artist_first`: used to indicate that your Beatcloud tracks adhere to the `Artist1, Artist2 - Title (Artist2 Remix)` format rather than the `Title (Artist2 Remix) - Artist1, Artist2` format expected by default 
* `log_level`: logger log level
* `verbosity`: verbosity level for logging messages

## [Collection config][djtools.collection.config.CollectionConfig]
* `collection_path`: the full path to your collection...the parent directory where this points to is also where all other collections generated or utilized by this library will exist
* `collection_playlists`: boolean flag to trigger the generation of a playlist structure (as informed by `collection_playlists.yaml`) using the tags in `collection_path`...the resulting collection is the file at `collection_path`
* `collection_playlists_remainder`: whether tracks of remainder tags (those not specified in `collection_playlists.yaml`) will be placed in a `folder` called "Unused Tags" with individual tag playlists or a `playlist` called "Unused Tags"
* `collection_playlist_filters`: list of `PlaylistFilter` classes used to apply special filtering logic to tag playlists
* `copy_playlists`: list of playlists in `collection_path` to (a) have audio files copied and (b) have track data written to a new collection with updated locations
* `copy_playlists_destination`: path to copy audio files to
* `platform`: DJ platform used (e.g. `rekordbox`)
* `shuffle_playlists`: list of playlists that will have their tracks shuffled

## [Spotify config][djtools.spotify.config.SpotifyConfig]
* `reddit_client_id`: client ID for registered Reddit API application
* `reddit_client_secret`: client secret for registered Reddit API application
* `reddit_user_agent`: user-agent for registered Reddit API application
* `spotify_client_id`: client ID for registered Spotify API application
* `spotify_client_secret`: client secret for registered Spotify API application
* `spotify_playlists`: boolean flag to trigger the automatic generation or updating of Spotify playlists from subreddits
* `spotify_playlist_default_limit`: default number of tracks for a Spotify playlist
* `spotify_playlist_default_period`: default subreddit period for a Spotify playlist
* `spotify_playlist_default_type`: default subreddit filter type for a Spotify playlist
* `spotify_playlist_from_upload`: boolean flag to trigger automatic generation of updating of a Spotify playlist from the Discord webhook output of a user's music upload (output must be copied to the system clipboard)
* `spotify_playlist_fuzz_ratio`: the minimum Levenshtein similarity between a Spotify API track search result and a subreddit post title (if post is not directly a Spotify URL) to trigger the addition of that track to the corresponding Spotify auto-playlist
* `spotify_playlist_post_limit`: the maximum number of posts to retrieve from a subreddit
* `spotify_playlist_subreddits`: list of `SubredditConfig` objects from which tracks should be added to Spotify auto-playlist; each element is a dictionary with keys for a subreddit's "name", "type", "period", and "limit"
* `spotify_redirect_uri`: redirect URI for registered Spotify API application
* `spotify_username`: Spotify username that will keep playlists automatically generated

## [Sync config][djtools.sync.config.SyncConfig]
* `aws_profile`: the name of the profile used when running `aws configure --profile`
* `aws_use_date_modified`: up/download files that already exist at the destination if the date modified field at the source is after that of the destination...BE SURE THAT ALL USERS OF YOUR `BEATCLOUD` INSTANCE ARE ON BOARD BEFORE UPLOADING WITH THIS FLAG SET!
* `bucket_url`: URL for an AWS S3 API compliant storage location
* `discord_url`: webhook URL for messaging a Discord server's channel when new music has been uploaded to the `beatcloud`
* `download_collection`: sync the collection of `import_user` from the `beatcloud` to the directory that `collection_path` is in
* `download_exclude_dirs`: the list of paths (relative to the `DJ Music` folder on your `usb_path`) that should NOT be downloaded from the `beatcloud` when running the `download_music` sync operation
* `download_include_dirs`: the list of paths (relative to the `DJ Music` folder on your `usb_path`) that should exclusively be downloaded from the `beatcloud` when running the `download_music` sync operation
* `download_music`: sync beatcloud to "DJ Music" folder
* `download_spotify_playlist`: if this is set to the name of a playlist (present in `spotify_playlists.yaml`), then only the Beatcloud tracks present in this playlist will be downloaded
* `dryrun`: show `aws s3 sync` command output without running
* `import_user`: the username of a fellow `beatcloud` user whose collection you want to download
* `upload_collection`: sync `collection_path` to the beatcloud
* `upload_exclude_dirs`: the list of paths (relative to the `DJ Music` folder on your `usb_path`) that should NOT be uploaded to the `beatcloud` when running the `upload_music` sync operation
* `upload_include_dirs`: the list of paths (relative to the `DJ Music` folder on your `usb_path`) that should exclusively be uploaded to the `beatcloud` when running the `upload_music` sync operation
* `upload_music`: sync "DJ Music" folder to the beatcloud
* `usb_path`: the full path to the USB drive which contains all your music files
* `user`: this is the username of the current user...if left as an empty string, then your operating system username will be used...it's recommended that you only override this if your username changes from what other users of your `beatcloud` instance are expecting (to ensure consistency...i.e. when you get a new computer with a different username)

## [Utils config][djtools.utils.config.UtilsConfig]
* `audio_bitrate`: string representing the integer in the range [`36`, `320`] for the bitrate to write audio at e.g. `"320"`
* `audio_destination`: path to where downloaded and / or exported files go to
* `audio_format`: string representing the file format write audio in e.g. `"mp3"`
* `audio_headroom`: non-negative float representing the amount of headroom in decibels to leave when normalizing audio
* `check_tracks`: boolean flag to trigger checking the contents of the `beatcloud` (to identify redundancies)
* `check_tracks_fuzz_ratio`: the minimum Levenshtein similarity for indicating potential redundancies between Spotify playlists / local directories and the `beatcloud`
* `check_tracks_spotify_playlists`: list of Spotify playlists to use with `check_tracks` (must exist in `spotify_playlists.yaml`)
* `local_dirs`: list of local directories to use with `check_tracks`
* `normalize_audio`: boolean flag to trigger normalizing audio files at `local_dirs`,
* `process_recording`: boolean flag to trigger processing an audio recording using a Spotify playlist
* `recording_file`: Audio recording to pair with `recording_playlist`
* `recording_playlist`: Spotify playlist to pair with `recording_file`
* `trim_initial_silence`: Milliseconds of initial silence to trim off `recording_file`. Can also be a negative integer to prepend silence. Can also be "auto" or "smart" for automatic silence detection or a home-brewed algorithm for finding the optimal offset.
* `url_download`: URL from which music files should be downloaded (i.e. a Soundcloud playlist)
