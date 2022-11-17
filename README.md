# DJ Tools
[![image](https://img.shields.io/pypi/v/dj-beatcloud.svg)](https://pypi.org/project/dj-beatcloud/)

## Contents
* Release Plan
* Overview
* Setup
    - Python
    - AWS
* Usage
    - Linking configs
    - Populating `config.json`
        * Example `config.json`
        * Explanation of configuration options
* Contribution
* Basic Information
    - Preliminary
        * Music files
            * Format
            * Allowed characters
            * Standardization
        * Rekordbox XML
    - Importing tracks from Explorer
    - Setting beatgrid and hot cues
    - Importing tracks from XML
    - Reloading tags
    - Exporting to a Device
# Release Plan
* 2.2.2
    - `spotify.playlist_builder`
        - [ ] Improved Reddit post parsing and Spotify searching
* 2.3.0
    - `rekordbox`
        - [x] Playlist organization by Rekordbox "My Tags"
        - [x] boolean algebra for tags ("My Tags" and "Genres")
    - `utils`
        - [x] Copying audio files from playlists

# Overview
`DJ Tools` is a library for managing a Collection of audio files (not necessarily mp3 files, although that is preferred) and Rekordbox XML files.

To take full advantage of this library, users must:
1. have access to an AWS S3 instance or another AWS S3 API compliant object store such as [MinIO](https://min.io/) (the `beatcloud`) and have the `awscli` client configured to reach it
2. be a Rekordbox user (for functions of the `rekordbox` package)
3. keep your Collection on a USB drive
4. use the following naming convention for music files in your Collection:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Title (Artist2 Remix) - Artist1, Artist2`

5. utilize the `Genre` tags in your Collection
5. utilize the `My Tags` tags in your Collection
7. have a Spotify account (for `spotify.playlist_builder`)

The core functionality of this library can be broken up into four sub-packages:
1. `sync`: allows users to push and pull audio and Rekordbox XML files to and from the `beatcloud`
2. `spotify`: allows users to:
    * compare the tracks of one or more Spotify playlists against the `beatcloud` (to identify redundancies)
    * update Spotify playlists using the titles / links of Reddit submissions
3. `rekordbox`: operates on an exported XML Rekordbox database file to:
    * automatically generate playlists based on the tags of your Collection
    * emulating a playlist randomization feature which is strangely absent from Rekordbox
4. `utils`: contains a variety of utilities for things such as:
    * downloading mp3 files from a URL (e.g. Soundcloud...don't use YouTube because that's some highly compressed garbage)
    * copmare the tracks of one or more local directories against the `beatcloud` (to identify redundancies)
    * copy audio files from a given playlist to a new location and generate a new XML for those files (for backups and ensuring you can play a preparation on non-Pioneer setups)

For usage details relating to the individual packages of `DJ Tools`, checkout the README files that are [collocated with those packages](https://github.com/a-rich/DJ-Tools/tree/main/src/djtools).

# Setup

## Python
1. The `DJ Tools` library uses f-strings so a minimum version of Python 3.6 is required. As always, when working with a Python project, you're going to want to create a virtual environment; [Pyenv](https://github.com/pyenv/pyenv) is really nice, but if you insist on doing a system-wide python installation then proceed with the following instructions:
    - Mac installation: `brew install python@3.6`
    - Linux installation: `sudo apt install python3.6`
    - Windows installation: [Windows releases](https://www.python.org/downloads/windows/) or [3.6.0 installer](https://www.python.org/ftp/python/3.6.0/python-3.6.0.exe)

2. Run `pip install "dj-beatcloud[levenshtein]"` to install the DJ Tools library.
3. You can install the pre-release version with `pip install "dj-beatcloud[levenshtein]" --pre`
    - if you want to restrict the version being installed to not include, say, the next minor version's beta release then you can do so like `pip install "dj-beatcloud[levenshtein]<2.3.0" --pre`
    - note that installing with the `--pre` flag will also install pre-release versions for all dependencies which may cause breakage

`NOTE`: operations that involve computing the similarity between track names (both modules in the `spotify` package, the `utils.local_dirs_checker` module, and the `swap_title_artist` repair script) can be made much faster by installing the `python-Levenshtein` package; Windows users may find it more cumbersome to install `DJ Tools` this way though since they may not have the required C++ binaries to run the Levenshtein operations...if this applies to you, then ommit the `[levenshtein]` part:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`pip install dj-beatcloud`

You can always install the necessary package to accelerate computing at a later time:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`pip install python-Levenshtein`

## AWS
1. Next you will need to configure `awscli` to access your instance of the `beatcloud`. The Python package `awscli` should have been installed during the `pip` install of the previous step, but in the event that you cannot run the `aws` command, you'll have to install it the long way:
    - Mac installation: `brew install awscli`
    - Linux installation: `sudo apt-get install awscli`
    - Windows installation [[official instructions](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-windows.html)]: [download installer](https://awscli.amazonaws.com/AWSCLIV2.msi) OR run:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi`

2. Now configure `awscli` to connect to your `beatcloud` instance:


&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`aws configure --profile DJ`

3. Enter the `access_key` and `secret_key`. Default values for the rest of the configuration is fine.

`NOTE`: it is not strictly required that users signup for an AWS account and pay for an S3 bucket. As Reddit user `/u/beachshells` noted, there are S3 API compliant alternatives that allow you to host your own object-storage server such as [MinIO](https://min.io/).

# Usage
## Linking configs
You should now be able to run `djtools` from anywhere, although nothing will work until you've populated the required `config.json`.

Because this `config.json` file (and all other JSON files used by this library) live next to the package code (somewhere not user-friendly), it's recommended that you choose a non-existent directory (e.g. `djtools_configs`) and run this command first to establish a user-friendly location where you can create and modify your config files:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`djtools --link_configs /path/to/djtools_configs/`

After running this command, base templates for all config files used by `djtools` will be symlinked allowing you to navigate to that directory and open `config.json` (and all other config files) with your favorite text editor and configure the library for your needs.

Please be sure to checkout the package-level README files regarding the usage of the other config files which must also be stored in the same location as `config.json`:
* `spotify`
    - [playlist_builder.json](https://github.com/a-rich/DJ-Tools/tree/main/src/djtools/spotify)
    - [playlist_checker.json](https://github.com/a-rich/DJ-Tools/tree/main/src/djtools/spotify)
* `sync`
    - [registered_users.json](https://github.com/a-rich/DJ-Tools/tree/main/src/djtools/sync)
* `rekordbox`
    - [rekordbox_playlists.json](https://github.com/a-rich/DJ-Tools/tree/main/src/djtools/rekordbox)

## Populating `config.json`
`DJ Tools` contains quite a bit of functionality, but all of it is configurable via `config.json`. You may decide to not use `config.json` at all and, instead, opt to use the corollary command-line arguments; all configuration options may be overridden via command-line arguments of the same name but in lowercase. Example:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`djtools --download_xml --xml_import_user bob --aws_profile DJ`


### Example `config.json`:
```
{
    "USB_PATH": "/Volumes/My_DJ_USB/",
    "AWS_PROFILE": "DJ",
    "UPLOAD_INCLUDE_DIRS": [],
    "UPLOAD_EXCLUDE_DIRS": ["New Music"],
    "DOWNLOAD_INCLUDE_DIRS": [],
    "DOWNLOAD_EXCLUDE_DIRS": [],
    "AWS_USE_DATE_MODIFIED": false,
    "XML_IMPORT_USER": "myfriend",
    "XML_PATH": "/path/to/xmls/my_rekordbox.xml",
    "USER": "",
    "DISCORD_URL": "https://discord.com/api/webhooks/some/url",
    "YOUTUBE_DL": false,
    "YOUTUBE_DL_URL": "https://soundcloud.com/me/sets/to-download",
    "RANDOMIZE_TRACKS": false,
    "RANDOMIZE_TRACKS_PLAYLISTS": ["Halftime", "Trip Hop"],
    "DOWNLOAD_MUSIC": false,
    "DOWNLOAD_XML": false,
    "UPLOAD_MUSIC": false,
    "UPLOAD_XML": false,
    "REKORDBOX_PLAYLISTS": false,
    "REKORDBOX_PLAYLISTS_REMAINDER": "folder",
    "GENRE_PLAYLISTS_PURE": [],
    "CHECK_TRACK_OVERLAP": false,
    "CHECK_TRACK_OVERLAP_FUZZ_RATIO": 80,
    "LOCAL_CHECK_DIRS": ["New Music"],
    "SPOTIFY_CHECK_PLAYLISTS": ["Download", "Maybe Download"],
    "SPOTIFY_CLIENT_ID": "",
    "SPOTIFY_CLIENT_SECRET": "",
    "SPOTIFY_REDIRECT_URI": "",
    "SPOTIFY_USERNAME": "",
    "AUTO_PLAYLIST_UPDATE": false,
    "AUTO_PLAYLIST_SUBREDDITS": [
        {"name": "HalftimeDnB", "type": "hot", "period": "week", "limit": 50},
        {"name": "spacebass", "type": "top", "period": "week", "limit": 50}
    ],
    "AUTO_PLAYLIST_FUZZ_RATIO": 50,
    "AUTO_PLAYLIST_SUBREDDIT_LIMIT": 500,
    "REDDIT_CLIENT_ID": "",
    "REDDIT_CLIENT_SECRET": "",
    "REDDIT_USER_AGENT": "",
    "VERBOSITY": 0,
    "LOG_LEVEL": "INFO"
}
```
### Explanation of configuration options
* `USB_PATH`: the full path to the USB drive which contains all your music files
* `AWS_PROFILE`: the name of the profile used when running `aws configure --profile`
* `UPLOAD_INCLUDE_DIRS`: the list of paths to folders (relative to the `DJ Music` folder on your `USB_PATH`) that should exclusively be uploaded to the `beatcloud` when running the `upload_music` sync operation
* `UPLOAD_EXCLUDE_DIRS`: the list of paths to folders (relative to the `DJ Music` folder on your `USB_PATH`) that should NOT be uploaded to the `beatcloud` when running the `upload_music` sync operation
* `DOWNLOAD_INCLUDE_DIRS`: the list of paths to folders (relative to the `DJ Music` folder on your `USB_PATH`) that should exclusively be downloaded from the `beatcloud` when running the `download_music` sync operation
* `DOWNLOAD_EXCLUDE_DIRS`: the list of paths to folders (relative to the `DJ Music` folder on your `USB_PATH`) that should NOT be downloaded from the `beatcloud` when running the `download_music` sync operation
* `AWS_USE_DATE_MODIFIED`: up/download files that already exist at the destination if the date modified field at the source is after that of the destination (i.e. the ID3 tags have been changed)...BE SURE THAT ALL USERS OF THIS `BEATCLOUD` INSTANCE ARE ON BOARD BEFORE UPLOADING WITH THIS FLAG SET!
* `XML_IMPORT_USER`: the username of a fellow `beatcloud` user (as present in `registered_users.json`) from whose Rekordbox XML you are importing tracks
* `XML_PATH`: the full path to your Rekordbox XML file which should contain an up-to-date export of your Collection...the directory where this points to is also where all other XMLs generated or utilized by this library will exist
* `USER`: this is the username that will be entered into `registered_users.json`...if left as an empty string, then your operating system username will be used...it's recommended that you only override this if your username changes from what other users of your `beatcloud` instance are expecting (to ensure consistency)
* `DISCORD_URL`: webhook URL for messaging a Discord server's channel when new music has been uploaded to the `beatcloud`
* `YOUTUBE_DL`: boolean flag to trigger the downloading of files from `YOUTUBE_DL_URL` into the `DJ Music` -> `New Music` folder on your `USB_PATH`
* `YOUTUBE_DL_URL`: URL from which music files should be downloaded (i.e. a Soundcloud playlist)
* `RANDOMIZE_TRACKS`: boolean flag to trigger the emulated playlist shuffling feature on each playlist in `RANDOMIZE_TRACKS_PLAYLISTS`
* `RANDOMIZE_TRACKS_PLAYLISTS`: list of playlist names (must exist in `XML_PATH`) that should have their tracks shuffled
* `DOWNLOAD_MUSIC`: sync remote beatcloud to "DJ Music" folder
* `DOWNLOAD_XML`: sync remote XML of `XML_IMPORT_USER` to parent of `XML_PATH`
* `UPLOAD_MUSIC`: sync local "DJ Music" folder to the beatcloud
* `UPLOAD_XML`: sync local `XML_PATH` to the beatcloud
* `REKORDBOX_PLAYLISTS`: boolean flag to trigger the generation of a playlist structure (as informed by `rekordbox_playlists.json`) using the tags in `XML_PATH`...the resulting XML file is `XML_PATH` prefixed with "`auto_`"
* `REKORDBOX_PLAYLISTS_REMAINDER`: whether tracks of remainder tags (those not specified in `rekordbox_playlists.json`) will be placed in a `folder` called "Other" with individual tag playlists or a `playlist` called "Other"
* `GENRE_PLAYLISTS_PURE`: list of genre tags (case-sensitive) which will each have a "Pure" playlist generated for...each item must be accompanied with a "Pure \<genre>" entry in `rekordbox_playlists.json`,
* `CHECK_TRACK_OVERLAP`: boolean flag to trigger checking the contents of Spotify playlists specified in `SPOTIFY_CHECK_PLAYLISTS` and the local files specified in `LOCAL_CHECK_DIRS` against the `beatcloud` (to identify redundancies)
* `CHECK_TRACK_OVERLAP_FUZZ_RATIO`: the minimum Levenshtein similarity for indicating potential redundancies between Spotify playlists / local directories and the `beatcloud`
* `LOCAL_CHECK_DIRS`: list of local directories (under "DJ Music") to use with `CHECK_TRACK_OVERLAP`,
* `SPOTIFY_CHECK_PLAYLISTS`: list of Spotify playlists to use with `CHECK_TRACK_OVERLAP`
* `SPOTIFY_CLIENT_ID`: client ID for registered Spotify API application
* `SPOTIFY_CLIENT_SECRET`: client secret for registered Spotify API application
* `SPOTIFY_REDIRECT_URI`: redirect URI for registered Spotify API application
* `AUTO_PLAYLIST_UPDATE`: boolean flag to trigger the automatic generation or updating of Spotify playlists from subreddits
* `SPOTIFY_USERNAME`: Spotify username that will keep playlists automatically generated
* `AUTO_PLAYLIST_SUBREDDITS`: list of subreddits from which tracks should be added to Spotify auto-playlist; each element is a dictionary with keys for subreddit's "name", "type", "period", and "limit"
* `AUTO_PLAYLIST_FUZZ_RATIO`: the minimum Levenshtein similarity between a Spotify API track search result and a subreddit post title (if post is not directly a Spotify URL) to trigger the addition of that track to the corresponding Spotify auto-playlist
* `AUTO_PLAYLIST_SUBREDDIT_LIMIT`: the maximum number of posts to retrieve from a subreddit
* `REDDIT_CLIENT_ID`: client ID for registered Reddit API application
* `REDDIT_CLIENT_SECRET`: client secret for registered Reddit API application
* `REDDIT_USER_AGENT`: user-agent for registered Reddit API application
* `VERBOSITY`: verbosity level for logging messages
* `LOG_LEVEL`: logger log level

# Contribution
If you wish to contribute to `DJ Tools`, please follow these development rules:
1. Only release branches (`major: 3.0.0`, `minor: 2.3.0`, `patch: 2.2.2`) can be made off of `main`
2. The only commits to `main` that are allowed are updates to the `Release Plan` portion of this `README`
3. New features are added to the next minor release branch which will be created and released quarterly (the 1st of January, April, July, and October)
4. Bug fixes are added to the next patch release branch which will be created whenever the last is published to PyPI
5. Non-release branches must have a concise name for the feature or bugfix specifically targeted by that branch (e.g. `xml-track-randomization`)
6. If collaborating on a feature/fix with another user, prefix the feature/fix branch name with `username/`

# Basic Information
If you are an advanced Rekordbox user, then the following section is likely not for you. If you are not an advanced Rekordbox user, or are interested in the workflow patterns that accompany this library, read on!

## Preliminary

### Music files
#### Format
The music files in your Collection _should_ be in the MP3 format. There are a couple reasons for this:
1. MP3 files are very compact meaning you can fit more music on your USB, pay less for cloud storage, and enjoy faster upload / download times
2. MP3 files have metadata fields called ID3 tags which couple information like track, title, artist, comment, genres, etc. with the file itself; other formats (AIFF or WAV) _may_ include implementations of ID3 but this library has not been tested with these

It's true that MP3 is lossy, meaning it's _possible_ for MP3 files to produce lower quality audio than, say, FLAC files, but [research](https://www.researchgate.net/publication/257068576_Subjective_Evaluation_of_MP3_Compression_for_Different_Musical_Genres) (see [Nyquist–Shannon sampling theorem](https://en.wikipedia.org/wiki/Nyquist%E2%80%93Shannon_sampling_theorem)) shows that even the most trained ears of audiophiles cannot distinguish any difference between lossless audio and 256 kbps MP3 audio. There _are_ arguments that support using a sample rate higher than the theoretical minimum for human hearing (44.1 kHz); digital-to-analog conversion (as is performed in a speaker cone) is necessarily a non-linear system which can produce audible distortions from previously inaudible frequencies. Since my audio processing facilities support the highest quality bitrate for MP3 files, and the size of these files is negligibly larger, I use 320 kbps files.

#### Allowed characters
The characters you use in the filenames added to the beatcloud _does_ matter; while Unix systems are very tolerant of filenames, Windows systems are comparably very sensitive. Windows explicitly lists these characters as forbidden: `<`, `>`, `:`, `"`, `/`, `\`, `|`, `?`, `*`, `%`, `?`

Futher more, files stored in S3 may not interact properly with the protocols that may be used to sync them if they contain particular characters. I cannot speak to character related compatibility issues with other object-storage solutions.

Lastly, the `djtools` package wraps paths in double-quotes `"` so these MUST NOT be used in filenames!

I'm advocating that the character set matched by this regex expression be the whitelist of characters for filenames:

```
In [2]: string = "Track_Title (Artist2 Remix) ['Things' & Stuff!] - Artist1, Artist2.mp3"

In [3]: pattern = r"[0-9 a-z A-Z _ ' & \( \) \[ \] \s \- , . !]+"

In [4]: re.match(pattern, string).group(0)
Out[4]: "Track_Title (Artist2 Remix) ['Things' & Stuff!] - Artist1, Artist2.mp3"
```

In general:
* keep the filenames as close as possible to the `Title (Artist2 Remix) - Artist1, Artist2` format
* ensure there is only one instances of a hyphen with spaces on each side; title / artist splitting for `spotify.playlist_checker` and `utils.local_dirs_checker` will not work properly without this
* if the source is Spotify, try to match the fields as close as possible; e.g. if the title includes `(Radio Edit)` then you should name the track accordingly
    - this is to ensure that `spotify.playlist_checker` and `utils.local_dirs_checker` work properly since the similarity of filenames are checked against Spotify API query results
* don't use accent marks, any of the explicitly listed characters disallowed by Windows, or any other weird / non-standard characters

#### Standardization
To ensure Collection consistency and successful operation of `DJ Tools`, the following properties should be maintained for all music files. **Users of my beatcloud _must_ complete a minimum of (1), (2), and (3) prior to uploading**. Since track title, artist names, and melodic key are objective, and populating these tags prior to uploading saves every other user from repeating these efforts, it is greatly appreciated if users also complete (4) and (5). Futhermore, it is advised that users complete (6) through (11) as well, although users should expect to redo these themselves when integrating others' tracks since they are mostly subjective (with the exception of `beatgrid` and, to some extent, `color`):

`NOTE`: obviously the manner in which any tags are used is up to the user; this is especially true for `comment` and `color` tags. However, `genre` and `My Tags` should be used for their intended purpose otherwise users won't be able to use the `rekordbox.rekordbox_playlist_builder` module.

1. MP3 file format
2. minimum 256 kbps bitrate (320 kbps preferred)
3. files named using convention: `Title (Artist2 Remix) - Artist1, Artist2`
4. `title` and `artist` tags populated (ideally using software such as [Mp3tag](https://www.mp3tag.de/en/) or [Picard](https://picard.musicbrainz.org/))
5. `key` tags populated (ideally using Mixed In Key)
6. `genre` tags populated (split with a common delimiter of `/` if multiple genres)
7. `My Tags` tags populated
8. `beatgrid` should be set correctly
9. `hot cues` should be set the expected schema
10. `comment` tags 1st cleared and then populated with important information
    - BPM changes
    - unmixable (arrhythmic, ambient, or unstable BPM)
    - low quality
11. `color` tags
    - `GREEN` for fully processed track
    - `YELLOW` to warn of tricky or absent beatgrids, mid-song BPM changes, etc.
    - `RED` to warn of low quality or otherwise unmixable tracks

Mixed In Key is the most accurate key analysis software out there and is _much_ better than Rekordbox's key analysis. Make sure you turn off `KEY` under `Preferences > Analysis > Track Analysis Setting` so as to not overwrite `key` tags generated by MIK when importing tracks into Rekordbox.

![alt text](https://raw.githubusercontent.com/a-rich/DJ-Tools/main/images/Pioneer_Preferences_Analysis.png "Turn off Rekordbox key analysis")

---

### Rekordbox XML
Your Rekordbox Collection includes all the data associated with individual tracks as well as playlist data. Your Collection can be exported to an XML file using `File > Export Collection in xml format`. The resulting file can be used to restore your Collection if it's ever lost or messed up. It's recommended that you make frequent backups of your Collection.

Because all track information is stored in the XML and tracks can be imported to a Collection from an XML, it's possible for multiple users to benefit from the efforts of another user who processes tracks in a shared Collection. For example, users `A` and `B` can both contribute audio files to the `beatcloud` while only user `A` prepares beatgrids, hot cues, genre tags, and playlists. After user `A` completes this work, exports an XML, and uploads said XML to the `beatcloud`, user `B` can then download that XML and use it to import tracks into their Collection _with_ all the data that user `A` generated.

---

## Importing tracks from Explorer
If you are importing unprocessed tracks for the first time, or you simply don't want to import other users' track data, then you will import tracks from the `Explorer` tree view (make sure it's set to visible under `Preferences > View > Layout`; see the image below). Upon importing, Rekordbox will perform an analysis which will attempt to set the beatgrid. Often times this is incorrect, so make sure you confirm it's correct before considering the track fully imported.

---

## Setting beatgrid and hot cues
A track's beatgrid is a set of data points which define the beats-per-minute (BPM) of a track and also, in the case of a dynamic beatgrid, define points where the BPM changes. Dynamic beatgrids are particularly handy for tracks that have one or more BPM changes but are otherwise BPM stable (the track is quantized or recorded to a metronome). Setting a dynamic beatgrid for tracks with unstable BPMs is often more effort than it's worth and generally produces, at best, a track that gives the illusion of being easy to mix while, in practice, this is not the case.

When importing a track, there are several beatgrid-related states that the built-in analysis may produce (in order of correctness):
1. BPM is correct and beatgrid is aligned correctly
2. BPM is correct but beatgrid is misaligned (requires a simple shift)
3. BPM is incorrect (often requires alternating between BPM adjustements and beatgrid shifts)
4. track has severely unstable BPM (I generally forgo setting the beatgrid, turn off quantization, and set my hot cues as desired)

Once the beatgrid is established, I will apply a standardized hot cue schema so that I can reliably mix any track in my library, even if it's quite old and I've forgotten its nuances. Below is a description of the schema that I personally use for all my tracks:

* `A` and `B`: beat on which a break or build starts (in chronological order)
* `C`: "best" downbeat to begin a mix on (not too high energy, but definitely a prominent downbeat)
* `D`, `G`, `H`: chronologically successive "drops" of the track (generally following a break / build)
* `E`: the very first sound of the track (not necessarily a downbeat)
* `F`: warning flag that the track is close to finishing or approaching a significant dropoff in energy (usually 8 or 16 bars before said dropoff / end)

---

## Importing tracks from XML
Make sure you have made the `rekordbox.xml` database visible under `Preferences > View > Layout`:

![alt text](https://raw.githubusercontent.com/a-rich/DJ-Tools/main/images/Pioneer_Preferences_View.png "Show XML database in side panel")

Also ensure you have the proper XML file selected under `Preferences > Advanced > Database > rekordbox xml`:

![alt text](https://raw.githubusercontent.com/a-rich/DJ-Tools/main/images/Pioneer_Preferences_Database.png "Select XML database")

Then select the track(s), playlist(s), or folder(s) and choose "Import To Collection" or "Import Playlist"; this will overwrite playlists, beatgrids, hot cues, and Rekordbox Tags for files / playlists / folders with the same name!

![alt text](https://raw.githubusercontent.com/a-rich/DJ-Tools/main/images/Pioneer_Importing.png "Import tracks to Collection")

---

## Reloading tags
Reloading tags repopulates the Rekordbox tags using data stored in the MP3 files' ID3 tags. Be careful though, information you edit in Rekordbox doesn't necessarily overwrite the files' ID3 tags; for example, modifying `genre` tags in Rekordbox _does_ edit the ID3 tags but modifying `comment` tags _does not_. You may inadvertently overwrite your hard work to cleanup `comment` tags by running `Reload Tags`! If you want data either generated by another `beatcloud` user or by utilities, like `rekordbox_playlists` or `randomize_tracks`, you must reimport those tracks / playlists in Rekordbox rather than `Reload Tags`.

![alt text](https://raw.githubusercontent.com/a-rich/DJ-Tools/main/images/Pioneer_Reload_Tags.png "Reloading Tags")

---

## Exporting to a Device
Exporting to a Device is necessary if you want to have access to your Collection on CDJ hardware, Pioneer all-in-one controllers, or another Rekordbox user's laptop (if any USB, besides your own, is set as the Database `Preferences > Advanced > Database > Database management`). You can export your entire Playlists tree tab (as shown in this image) or any folders / playlists you select inside the Playlists tree tab by right-clicking the playlist / folder.

![alt text](https://raw.githubusercontent.com/a-rich/DJ-Tools/main/images/Pioneer_Export_Device.png "Exporting Device")
