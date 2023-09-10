# Usage
What follows is a basic introduction to using DJ Tools. For detailed usage of the different features provided, please see the [How-to Guides](../../how_to_guides/index.md).

DJ Tools is a command-line interface (CLI) tool so it must be run from the command-line! The command `djtools` should be available to you from any directory, however, Windows users may need to add their Python installation to their [PATH environment variable](https://www.wikihow.com/Change-the-PATH-Environment-Variable-on-Windows) depending on how they installed Python.

Upon a fresh installation, running `djtools` without any options should do nothing. All of the configuration options will take on the default values defined in the [configuration objects](configuration.md) which are the same values present in the pre-packaged [YAML](https://en.wikipedia.org/wiki/YAML) file, [config.yaml](https://github.com/a-rich/DJ-Tools/blob/main/djtools/configs/config.yaml).

Any of these options can be overridden from the CLI by providing the equivalent lowercase and dash-delimited option. For example, to activate the `collection_playlists` function, overriding whatever may be set for `COLLECTION_PLAYLISTS` in `config.yaml` can be done by running `djtools --collection-playlists`. The same options in `config.yaml` are UPPERCASE and underscore-delimited. For example, configuring the `collection_playlists` function to run every time you call `djtools` can be done by setting `COLLECTION_PLAYLISTS: true`.

Many of the configuration options are set only when first installing DJ Tools. Below are some example options that fit this category:

* `AWS_PROFILE`
* `COLLECTION_PATH`
* `SPOTIFY_CLIENT_ID`
* `DISCORD_URL`
* `USB_PATH`

For some other options, you will likely want to set them on a case-by-case basis and keep them configured at their default value, overriding them with the associated CLI option as needed. Some examples for this category include:

* `COLLECTION_PLAYLISTS`
* `SPOTIFY_PLAYLIST_UPDATE`
* `SPOTIFY_PLAYLIST_FROM_UPLOAD`
* `UPLOAD_COLLECTION`
* `DOWNLOAD_MUSIC`
* `CHECK_TRACKS`
* `IMPORT_USER`

Other options may change on occasion but are too difficult to format using the CLI, meaning you'll want to handle setting those options in `config.yaml`. Some example options that fit this category are:

* `SPOTIFY_PLAYLIST_SUBREDDITS`
* `DOWNLOAD_EXCLUDE_DIRS`
* `CHECK_TRACKS_SPOTIFY_PLAYLISTS`

## Linking your configs

Although it's not necessary to do so, it's recommended that users run `djtools --link-configs path/to/new/folder` in order to create a symbolic link from the `configs` directory where DJ Tools is installed to a more user-friendly location.

For example, whenever I install the newest version of DJ Tools, I remove my linked location (after making sure I backup important changes):

`rm -rf ~/Desktop/dj-tools-configs/live/`

then I run the following command to re-link the installed configs directory to the folder I just removed:

`djtools --link-configs ~/Desktop/dj-tools-configs/live/`

and then I run this command to restore my configuration options from backups that I save whenever a new version of DJ Tools is released:

`cp ~/Desktop/dj-tools-configs/backups/2.4.0/* ~/Desktop/dj-tools-configs/live/`

`NOTE`: these are Unix shell commands and will not work on Windows.
