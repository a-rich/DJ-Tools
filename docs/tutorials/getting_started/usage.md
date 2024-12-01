# Usage
What follows is a basic introduction to using DJ Tools.
For detailed usage of the different features provided, please see the [How-to Guides](../../how_to_guides/index.md).

DJ Tools is a command-line interface (CLI) tool so it must be run from the command-line!
The command `djtools` should be available to you from any directory, however, Windows users may need to add their Python installation to their [PATH environment variable](https://www.wikihow.com/Change-the-PATH-Environment-Variable-on-Windows) depending on how they installed Python.

Upon a fresh installation, running `djtools` without any options will do nothing.
All of the configuration options will take on the default values defined in the [configuration objects](configuration.md).
Upon your first run of `djtools` a default `config.yaml` will be generated in the package directory (see the note below about linking configs).

You may edit the values in this `config.yaml` to override the default values.
For example, if you want the `collection_playlists` function to run every time you run `djtools`, this can be done by setting `collection_playlists: true`.
If you want to configure the location of your music, this can be done by setting `usb_path: /path/to/your/music`.
If any unsupported keys are added to `config.yaml`, `djtools` will fail because extra keys are forbidden.
If any keys are missing from `config.yaml`, the defaults will be assumed.

All options can be overridden from the CLI by providing the equivalent lowercase and dash-delimited option.
For example, activating the `collection_playlists` function can be done by running `djtools --collection-playlists`.
If you want to set your `usb_path` from the CLI during, say, a download music operation, this can be done by running `djtools sync --download-music --usb-path /path/to/your/music`. 

To reiterate, the order of option precedence is `CLI arguments > config.yaml > defaults`.

Many of the configuration options are intended to be set only when first installing DJ Tools.
Below are some example options that fit this category:

* `aws_profile`
* `collection_path`
* `spotify_client_id`
* `discord_url`
* `usb_path`

For some other options, you will likely want to set them on a case-by-case basis and keep them configured at their default value, overriding them with the associated CLI option as needed. Some examples for this category include:

* `collection_playlists`
* `spotify_playlist_from_upload`
* `upload_collection`
* `download_music`
* `check_tracks`
* `import_user`

Other options may change on occasion but are too difficult to format using the CLI, meaning you'll want to handle setting those options in `config.yaml`. Some example options that fit this category are:

* `spotify_playlist_subreddits`
* `download_exclude_dirs`
* `check_tracks_spotify_playlists`

## Linking your configs
Although it's not necessary to do so, it's recommended that users run `djtools --link-configs path/to/new/folder` in order to create a symbolic link from the `configs` directory where DJ Tools is installed to a more user-friendly location.

For example, whenever I install the newest version of DJ Tools, I remove my linked location (after making sure I backup important changes):

`rm -rf ~/Desktop/dj-tools-configs/live/`

install djtools:

`pip install djtools`

run the following command to link the installed configs directory:

`djtools --link-configs ~/Desktop/dj-tools-configs/live/`

and then I run this command to restore my configuration options from backups that I save whenever a new version of DJ Tools is released:

`cp ~/Desktop/dj-tools-configs/backups/2.4.0/* ~/Desktop/dj-tools-configs/live/`

`NOTE`: these are Unix shell commands and will not work on Windows.

## Backup your configs
Because your configs are stored alongside your `djtools` installation, reinstalling `djtools` will delete your config files!
Please keep a backup of your config files and, upon reinstalling `djtools`, you can copy them into either your installation folder or the symbolically linked folder of your choosing.
