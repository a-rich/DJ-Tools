# Configs

## Contents
* Overview
* More Info

# Overview
### The `configs` package contains the following configuration files:
* `config.yaml`: global config for the `djtools` library
* `rekordbox_playlists.yaml`: config for the `rekordbox` package's `REKORDBOX_PLAYLISTS` feature
* `spotify_playlists.yaml`: config for the `spotify` package's `AUTO_PLAYLIST_UPDATE` and `PLAYLIST_FROM_UPLOAD` features, the `sync` package's `DOWNLOAD_SPOTIFY` feature, and the `utils` package's `CHECK_TRACKS_SPOTIFY_PLAYLISTS` feature
* `registered_users.yaml`: config for the `sync` package's `DOWNLOAD_XML` feature used in combination with the `IMPORT_USER` option to rewrite the downloaded XML such that the tracks' Location fields point to `USER`'s `USB_PATH` rather than `IMPORT_USER`'s `USB_PATH`
* `logging.conf`: a configuration used to setup logging

### The `configs` package contains the following modules:
* `config.py`: a `BaseConfig` object with default attributes overridden by the `config.yaml` options keyed by `configs`
* `helpers.py`: functions for building all the configuration objects from `config.yaml` and overridding their values with any command-line arguments that may be provided

# More Info
### `config.yaml`:
The initial `config.yaml` contains all the supported configuration options. The top-level keys map package names to their respective configuration options. Options that either to not apply to a specific package or apply to multiple packages are assigned the `configs` keyspace. If `config.yaml` is left empty, the default options specified in the `BaseConfig` class, and the subclasses respective to each package, will hold; these can be overridden by supplying the corollary command-line argument. For example, the default `AWS_PROFILE` option is `"default"` but can be overridden by running `djtools --aws-profile MY_PROFILE` or setting it in `config.yaml`:
```
configs:
  AWS_PROFILE: MY_PROFILE
```

### `rekordbox_playlists.yaml`:
The initial `rekordbox_playlist.yaml` contains a subset of a personal configuration. This may not produce meaningful results for other users, but it also won't cause any errors. Configuration of the `rekordbox_playlists.yaml` can be quite complciated which is why an example config file is provided. Successful usage of the `REKORDBOX_PLAYLISTS` feature depends on users exporting a Rekordbox XML with Genre and My Tag information included. For more information, please see the [README](../rekordbox/README.md) for the `rekordbox` package.

### `spotify_playlists.yaml`:
The intial `spotify_playlists.yaml` is empty as it doesn't make sense to fill it with either dummy data or personal data. The required structure is a flat key, value mapping of playlist names to Spotify playlist IDs. For the `CHECK_TRACKS` module, the playlists can be named anything and are referred to in the list specified as `CHECK_TRACKS_SPOTIFY_PLAYLISTS`. However, the `AUTO_PLAYLIST_UPDATE`, `PLAYLIST_FROM_UPLOAD`, and `DOWNLOAD_SPOTIFY` features expect particular playlist names; these are populated automatically so there's no need to worry about setting them in this config. For more information, please see the [README](../spotify/README.md) for the `spotify` package.

### `registered_users.yaml`:
This file is used by the `sync` package's `DOWNLOAD_XML` feature. It contains `USER:USB_PATH` mappings. This mapping is needed to
1. download the `XML_PATH` of `IMPORT_USER` from the proper location in the Beatcloud
2. rewrite the XML such that the tracks' Location field points to the `USB_PATH` of `USER` instead of the `USB_PATH` of `IMPORT_USER`

The initial `registered_user.yaml` is empty. During regular operation of `djtools` it will automatically be populated with your operating system's username and whatever value you have configured for `USB_PATH`. However, this registry won't be updated with other users' information. In order to get the desired behavior when using `DOWNLOAD_XML`, you will have to either request other users of your Beatcloud to share the contents of their `registered_users.yaml` or else manually inspect the structure of your Beatcloud and the XMLs that are uploaded to infer these values. For more information, please see the [README](../sync/README.md) for the `sync` package.