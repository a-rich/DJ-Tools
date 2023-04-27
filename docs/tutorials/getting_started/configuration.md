# Configuration
When the `djtools` command is run, [build_config](djtools.configs.helpers.build_config) looks for a `config.yaml` in the package's `config` directory and creates a [BaseConfig](djtools.configs.config.BaseConfig) object using its values. If `djtools` was run with any CLI options, those values override whatever was set in `config.yaml`.

If `config.yaml`, or any of the values it might contain, is missing then the default values in the Python object are used instead. In fact, if `config.yaml` is missing, then a default one will be created by serializing the fully instantiated `BaseConfig` object. This makes it easy for users to then edit `config.yaml` to get the desired behavior without having to reference the API to see what options are available.

## Base config 
* `AWS_PROFILE`: the name of the profile used when running `aws configure --profile`
* `LOG_LEVEL`: logger log level
* `VERBOSITY`: verbosity level for logging messages
* `XML_PATH`: the full path to your Rekordbox XML file which should contain an up-to-date export of your Collection...the directory where this points to is also where all other XMLs generated or utilized by this library will exist

## Rekordbox config
* `BUILD_PLAYLISTS`: boolean flag to trigger the generation of a playlist structure (as informed by `rekordbox_playlists.yaml`) using the tags in `XML_PATH`...the resulting XML file is `XML_PATH` prefixed with "`auto_`"
* `BUILD_PLAYLISTS_REMAINDER`: whether tracks of remainder tags (those not specified in `rekordbox_playlists.yaml`) will be placed in a `folder` called "Other" with individual tag playlists or a `playlist` called "Other"
* `COPY_PLAYLISTS`: list of playlists in `XML_PATH` to (a) copy audio files to `COPY_PLAYLISTS_DESTINATION` and (b) write to a new XML with updated Location fields.
* `COPY_PLAYLISTS_DESTINATION`: path to copy audio files to.
* `PURE_GENRE_PLAYLISTS`: list of genre tags (case-sensitive) which will each have a "Pure" playlist generated for...each item must be accompanied with a "Pure \<genre>" entry in `rekordbox_playlists.yaml`,
* `SHUFFLE_PLAYLISTS`: list of playlist names (must exist in `XML_PATH`) that should have their tracks shuffled

## Spotify config
* `AUTO_PLAYLIST_DEFAULT_LIMIT`: default number of tracks for a Spotify playlist
* `AUTO_PLAYLIST_DEFAULT_PERIOD`: default subreddit period for a Spotify playlist
* `AUTO_PLAYLIST_DEFAULT_TYPE`: default subreddit filter type for a Spotify playlist
* `AUTO_PLAYLIST_FUZZ_RATIO`: the minimum Levenshtein similarity between a Spotify API track search result and a subreddit post title (if post is not directly a Spotify URL) to trigger the addition of that track to the corresponding Spotify auto-playlist
* `AUTO_PLAYLIST_POST_LIMIT`: the maximum number of posts to retrieve from a subreddit
* `AUTO_PLAYLIST_SUBREDDITS`: list of subreddits from which tracks should be added to Spotify auto-playlist; each element is a dictionary with keys for subreddit's "name", "type", "period", and "limit"
* `AUTO_PLAYLIST_UPDATE`: boolean flag to trigger the automatic generation or updating of Spotify playlists from subreddits
* `PLAYLIST_FROM_UPLOAD`: boolean flag to trigger automatic generation of updating of Spotify playlists from the Discord webhook output of users' music upload (output must be copied to the system clipboard)
* `REDDIT_CLIENT_ID`: client ID for registered Reddit API application
* `REDDIT_CLIENT_SECRET`: client secret for registered Reddit API application
* `REDDIT_USER_AGENT`: user-agent for registered Reddit API application
* `SPOTIFY_CLIENT_ID`: client ID for registered Spotify API application
* `SPOTIFY_CLIENT_SECRET`: client secret for registered Spotify API application
* `SPOTIFY_REDIRECT_URI`: redirect URI for registered Spotify API application
* `SPOTIFY_USERNAME`: Spotify username that will keep playlists automatically generated

## Sync config
* `AWS_USE_DATE_MODIFIED`: up/download files that already exist at the destination if the date modified field at the source is after that of the destination (i.e. the ID3 tags have been changed)...BE SURE THAT ALL USERS OF THIS `BEATCLOUD` INSTANCE ARE ON BOARD BEFORE UPLOADING WITH THIS FLAG SET!
* `DISCORD_URL`: webhook URL for messaging a Discord server's channel when new music has been uploaded to the `beatcloud`
* `DOWNLOAD_EXCLUDE_DIRS`: the list of paths to folders (relative to the `DJ Music` folder on your `USB_PATH`) that should NOT be downloaded from the `beatcloud` when running the `download_music` sync operation
* `DOWNLOAD_INCLUDE_DIRS`: the list of paths to folders (relative to the `DJ Music` folder on your `USB_PATH`) that should exclusively be downloaded from the `beatcloud` when running the `download_music` sync operation
* `DOWNLOAD_MUSIC`: sync remote beatcloud to "DJ Music" folder
* `DOWNLOAD_SPOTIFY`: if this is set to the name of a playlist (present in `spotify_playlists.yaml`), then the only Beatcloud tracks present in this playlist will be downloaded
* `DOWNLOAD_XML`: sync remote XML of `IMPORT_USER` to parent of `XML_PATH`
* `DRYRUN`: show `aws s3 sync` command output without running
* `IMPORT_USER`: the username of a fellow `beatcloud` user (as present in `registered_users.yaml`) from whose Rekordbox XML you are importing tracks
* `UPLOAD_EXCLUDE_DIRS`: the list of paths to folders (relative to the `DJ Music` folder on your `USB_PATH`) that should NOT be uploaded to the `beatcloud` when running the `upload_music` sync operation
* `UPLOAD_INCLUDE_DIRS`: the list of paths to folders (relative to the `DJ Music` folder on your `USB_PATH`) that should exclusively be uploaded to the `beatcloud` when running the `upload_music` sync operation
* `UPLOAD_MUSIC`: sync local "DJ Music" folder to the beatcloud
* `UPLOAD_XML`: sync local `XML_PATH` to the beatcloud
* `USB_PATH`: the full path to the USB drive which contains all your music files
* `USER`: this is the username that will be entered into `registered_users.yaml`...if left as an empty string, then your operating system username will be used...it's recommended that you only override this if your username changes from what other users of your `beatcloud` instance are expecting (to ensure consistency)

## Utils config
* `CHECK_TRACKS`: boolean flag to trigger checking the contents of Spotify playlists specified in `CHECK_TRACKS_SPOTIFY_PLAYLISTS` and the local files specified in `CHECK_TRACKS_LOCAL_DIRS` against the `beatcloud` (to identify redundancies)
* `CHECK_TRACKS_FUZZ_RATIO`: the minimum Levenshtein similarity for indicating potential redundancies between Spotify playlists / local directories and the `beatcloud`
* `CHECK_TRACKS_LOCAL_DIRS`: list of local directories (under "DJ Music") to use with `CHECK_TRACKS`,
* `CHECK_TRACKS_SPOTIFY_PLAYLISTS`: list of Spotify playlists to use with `CHECK_TRACKS`
* `URL_DOWNLOAD`: URL from which music files should be downloaded (i.e. a Soundcloud playlist)
* `URL_DOWNLOAD_DESTINATION`: path to download files to
