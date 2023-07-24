# Setup

## Python
The DJ Tools library uses [f-strings](https://peps.python.org/pep-0498/) and the [`asyncio` API](https://peps.python.org/pep-3156/) so a minimum version of Python 3.6 is required. As always, when working with a Python project, you're going to want to create a [virtual environment](https://docs.python.org/3/tutorial/venv.html); [Pyenv](https://github.com/pyenv/pyenv) is really nice but if you insist on doing a system-wide Python installation then proceed with the following instructions:

- Mac installation: `brew install python@3.6`
- Linux installation: `sudo apt install python3.6`
- Windows installation: [Windows releases](https://www.python.org/downloads/windows/) or [3.6.0 installer](https://www.python.org/ftp/python/3.6.0/python-3.6.0.exe)

Note that, at the time of writing, Python versions up through 3.7 have reached [end-of-life](https://devguide.python.org/versions/)...best to use at least Python 3.8.

## DJ Tools
1. Run `pip install "djtools[levenshtein]"` to install the DJ Tools library
    - To install DJ Tools without the accelerated computation for Levenshtein distance (might be difficult to install the binaries for non-technical users), run `pip install djtools`
    - You can install the pre-release version with `pip install djtools --pre`
    - If you want to restrict the version being installed to not include, say, the next minor version's beta release then you can do so like `pip install djtools<2.5.0 --pre`
    - Note that installing with the `--pre` flag will also install pre-release versions for all dependencies which may cause breakage, in that case you can target specific pre-release versions like this `pip install djtools==2.4.1-b9`
1. Confirm your installation works by running `djtools`
1. [Optional] link the `configs` directory of the installation to a user-friendly location for easy editing of your config files: `djtools --link-configs path/to/new/location/`
1. Edit your configuration files to support your usage needs ([see here for more details](configuration.md))

## AWS S3 API compliant object store
If you are using any of the following features, you are required to have an AWS S3 API compliant cloud storage account setup (see [this guide](../../how_to_guides/setup_object_storage.md) for more details):

* [Sync files with the Beatcloud](../../how_to_guides/sync_beatcloud.md)
* [Check the Beatcloud for tracks in Spotify playlists or local directories](../../how_to_guides/check_beatcloud.md)

## Spotify (and Reddit) API
If you are using any of the following features, you are required to have a registered Spotify API application (see [this guide](../../how_to_guides/reddit_spotify_api_access.md) for more details):

* [Create Spotify playlists from other users' uploads](../../how_to_guides/spotify_playlist_from_upload.md)
* [Sync tracks from Spotify playlists](../../how_to_guides/sync_spotify.md)
* [only if using the `CHECK_TRACKS_SPOTIFY_PLAYLISTS` option] [Check the Beatcloud for tracks in Spotify playlists or local directories](../../how_to_guides/check_beatcloud.md)

Additionally, if you're using any of the following features, you are required to have a registered Reddit API application (see [this guide](../../how_to_guides/reddit_spotify_api_access.md) for more details):

* [Create Spotify playlists from Reddit posts](../../how_to_guides/spotify_playlist_from_reddit.md)

## Spotify user account
If you are using any of the following features, you are required to have a Spotify account to add playlists to:

* [Create Spotify playlists from Reddit posts](../../how_to_guides/spotify_playlist_from_reddit.md)
* [Create Spotify playlists from other users' uploads](../../how_to_guides/spotify_playlist_from_upload.md)

## Discord webhook
If you are using any of the following features, you are required to have a Discord server with a registered webhook integration (see [this guide](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) for more details):

* [Create Spotify playlists from other users' uploads](../../how_to_guides/spotify_playlist_from_upload.md)
* [not strictly required, but uploading music is the corollary feature to the above] [Sync files with the Beatcloud](../../how_to_guides/sync_beatcloud.md#uploading-music)

## Rekordbox settings

### Writing "My Tag" data to the Comments field
In order for "My Tag" data to be accessible to the [Build Playlists From Tags](../../how_to_guides/collection_playlists.md) and [Combine Playlists With Boolean Algebra](../../how_to_guides/combiner_playlists.md) features, that data must be written to the Comments field. There's no need to clear pre-existing data from the Comments; just ensure that this option is checked in the settings:

![alt text](../../images/Pioneer_MyTag_Comments.png "Writing My Tag data to Comments")

### Importing tracks from XML
Make sure you have made the `rekordbox.xml` database visible under `Preferences > View > Layout`:
![alt text](../../images/Pioneer_Preferences_View.png "Show XML database in side panel")

Also ensure you have the proper XML file (whichever XML has data you're wanting to import) selected under `Preferences > Advanced > Database > rekordbox xml`:
![alt text](../../images/Pioneer_Preferences_Database.png "Select XML database")
