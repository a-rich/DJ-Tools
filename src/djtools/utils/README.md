# Utils

## Contents
* Overview
* Setup
* Usage

# Overview
The `utils` package contains modules:
* `generate_tags_playlists`: constructs tag playlists using tags in a Collection and a defined playlist structure in `generate_tags_playlists.json`
* `local_dirs_checker`: checks local tracks for overlap with those already in the beatcloud
* `randomize_tracks`: writes sequential numbers to Rekordbox tags of shuffled tracks in playlists to emulate playlist shuffling
* `youtube_dl`: downloads files from a URL to `DJ Music` -> `New Music`
* `helpers`: helper functions for top-level operations (`upload_log`)

# Setup
The `generate_tags_playlists` module requires that you utilize the genre ID3 / Rekordbox tag and / or "My Tags" feature for tracks in your Collection. It's also required that `XML_PATH` exists as well as a `generate_tags_playlists.json` in the `config` folder. Additionally, if any of your Collection's tracks have multiple genres specified in the genre tag field, they must be delimited with a `/` character.

The `local_dirs_checker` module requires that both `USB_PATH` exists and the directories listed in `LOCAL_CHECK_DIRS` exist under the "DJ Music" folder of `USB_PATH`.

The `randomize_tracks` module requires that both `XML_PATH` and `USB_PATH` exist. Additionally, playlists in `RANDOMIZE_TRACKS_PLAYLISTS` must exist inside `XML_PATH`.

The `youtube_dl` module requires that `USB_PATH` exists and that `YOUTUBE_DL_URL` is a valid URL from which MP3 files can be downloaded.

# Usage

## generate_tags_playlists
For the `generate_tags_playlists` module to run, there must be a `generate_tags_playlists.json` in the `config` folder. This JSON must be a dictionary with auto playlist types as keys (currently only "Genres" and "My Tags" are supported) and values as dictionaries with the follwing keys: a "name" key for the name of your playlist folder and a "playlists" key with a list of values which can be a combination of strings (playlist names matching genre / "My Tags" tags...case-sensitive) and dictionaries (subfolders with more playlists / subfolders inside them).

Any subfolder will implicitly have an `All <subfolder name>` playlist to collect all tracks that are inserted into playlists belonging to that subfolder. This operation is recursive ignoring the top-level folder.

You can insert a folder called "_ignore" anywhere in the structure except at the top-level and add a list of genres / "My Tags" to ignore in the "playlists" key. Tracks with these tags will not be inserted into the "Other" folder / playlist.

Here is an example `generate_tags_playlists.json`:
```
{
    "My Tags": {
        "name": "My Tags",
        "playlists": [
            "Vocal",
            "Synth",
            "Bass Music"
        ]
    },
    "Genres": {
        "name": "Genres",
        "playlists": [
            {
                "name": "_ignore",
                "playlists": [
                    "Psychedelic Rock",
                    "Soul"
                ]
            },
            {
                "name": "Bass",
                "playlists": [
                    {
                        "name": "Breaks",
                        "playlists": [
                            "Breakstep",
                            "Neurobreaks"
                        ]
                    },
                    {
                        "name": "Hip Hop Beats",
                        "playlists": [
                            "Halftime",
                            "Hip Hop"
                        ]
                    },
                    "Space Bass",
                    {
                        "name": "[___] Step",
                        "playlists": [
                            "Breakstep",
                            "Dubstep"
                        ]
                    }
                ]
            },
            "Hip Hop",
            {
                "name": "Techno",
                "playlists": [
                    "Pure Techno",
                    "Hard Techno"
                ]
            }
        ]
    }
}
```
The above structure generates a genre playlists folder like this:

![alt text](https://raw.githubusercontent.com/a-rich/DJ-Tools/main/images/Pioneer_Auto_Playlist.png "Automatic Genre Playlist")

and a "My Tags" playlists folder like this:

![alt text](https://raw.githubusercontent.com/a-rich/DJ-Tools/main/images/Pioneer_Auto_Playlist_My_Tags.png "Automatic My Tags Playlist")

There is special logic for creating "Pure" genre playlists; for example, say you want a "Pure Techno" playlist where the only tracks allowed in it have all genre tags containing the substring "techno". Simply add "techno" to the `GENERATE_GENRE_PLAYLISTS_PURE` list in `config.json`. Then add "Pure Techno" as a playlist in the desired location of your `generate_tags_playlists.json`. After running `djtools --generate_tags_playlists`, the resulting XML will contain this "Pure" genre playlist.

There is additional special logic regarding playlists called "Hip Hop". If a playlist with the name "Hip Hop" appears at the top-level of the playlists structure, then only tracks which have genre tags containing "Hip Hop" or both "Hip Hop" and "R&B" will be added. If the playlist is called "Hip Hop" and does not appear at the top-level of playlists, then only tracks that contain at least one tag which does not contain either "Hip Hop" or "R&B" will be added. The purpose of this is to distinguish between pure hip hop tracks and bass tracks which have hip hop elements.

To trigger the `generate_tags_playlists` module, set `GENERATE_TAGS_PLAYLISTS: true`. Additionally, you can set `GENERATE_TAGS_PLAYLISTS_REMAINDER` to either `folder` or `playlist` to place tracks belonging to tags not specified in `generate_tags_playlists.json` in either an "Other" folder of tag playlists or simply aggregate them all into an "Other" playlist.

Once the operation completes, an XML is generated at `XML_PATH` with the prefix `auto_`. Import your playlist structure from the XML.

## local_dirs_checker
To trigger the `local_dirs_checker` module, set `CHECK_TRACK_OVERLAP: true` and populate `lOCAL_CHECK_DIRS` with directories under the "DJ Music" directory.

## randomize_tracks
To trigger the `randomize_tracks` module, set `RANDOMIZE_TRACKS: true`. Once the operation has completed, you'll need to open Rekordbox and reimport the `AUTO_RANDOMIZE` playlist containing the set of tracks with updated `TrackNumber` fields.

## youtube_dl
To trigger the `youtube_dl` module, set `YOUTUBE_DL: true`. Once tracks are downloaded, make sure all file names adhere to convention:

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`Title (Artist2 Remix) - Artist1, Artist2.mp3`

After tracks are downloaded, you can follow the prescribed workflows specified under the main README's "Basic Information" section to ensure consistency both in your local library and in the `beatcloud`.
