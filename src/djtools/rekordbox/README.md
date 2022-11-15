# Playlist Builder

## Contents
* Overview
* Setup
* Usage

# Overview
The `rekordbox_playlist_builder` package contains modules:
* `randomize_tracks`: writes sequential numbers to Rekordbox tags of shuffled tracks in playlists to emulate playlist shuffling
* `rekordbox_playlist_builder`: constructs rekordbox playlists using tags in a Collection and a defined playlist structure in `rekordbox_playlists.json`

# Setup
The `randomize_tracks` module requires that both `XML_PATH` and `USB_PATH` exist. Additionally, playlists in `RANDOMIZE_TRACKS_PLAYLISTS` must exist inside `XML_PATH`.

The `rekordbox_playlist_builder` module requires that you utilize the genre ID3 / Rekordbox tag and / or "My Tags" feature for tracks in your Collection. It's also required that `XML_PATH` exists as well as a `rekordbox_playlists.json` in the `config` folder. Additionally, if any of your Collection's tracks have multiple genres specified in the genre tag field, they must be delimited with a `/` character.

# Usage

## randomize_tracks
To trigger the `randomize_tracks` module, set `RANDOMIZE_TRACKS: true`. Once the operation has completed, you'll need to open Rekordbox and reimport the `AUTO_RANDOMIZE` playlist containing the set of tracks with updated `TrackNumber` fields.

## rekordbox_playlist_builder 
For the `rekordbox_playlist_builder` module to run, there must be a `rekordbox_playlists.json` in the `config` folder. This JSON must be a dictionary with auto playlist types as keys (currently only "Genres", "My Tags", and "Combiner" are supported) and values as dictionaries with the following keys: "name" for the name of your playlist folder and "playlists" with a list of values which can be either strings (playlist names) or dictionaries (subfolders with more playlists / subfolders inside of them). Playlist names are case-sensitive and must match a single genre (for "Genres" playlists), a single "My Tags" tag (for "My Tags" playlists), or combinations of genres and "My Tags" expressed with boolean logic (for "Combiner" playlists). As an example of a "Combiner" configuration can be seen below

Any subfolder will implicitly have an `All <subfolder name>` playlist to collect all tracks that are inserted into playlists belonging to that subfolder. This operation is recursive ignoring the top-level folder.

You can insert a folder called "_ignore" anywhere in the structure except at the top-level and add a list of genres / "My Tags" to ignore in the "playlists" key. Tracks with these tags will not be inserted into the "Other" folder / playlist.

Here is an example `rekordbox_playlists.json`:
```
{
    "Combiner": {
        "name": "Combinations",
        "playlists": [
            "(Hard Techno & Acid Techno) | Minimal Techno",
            "Minimal House | Techno",
            "Bass House & Techno",
            "Breaks ~ Techno",
            "((Jungle | Breaks) ~ Techno) | (Garage ~ Tech House)"
        ]
    },

    "MyTagsParser": {
        "name": "My Tags",
        "playlists": [
            "Vocal",
            "Synth",
            "Bass Music"
        ]
    },
    "GenreTagsParser": {
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

![alt text](https://raw.githubusercontent.com/a-rich/DJ-Tools/2.3.0/images/Pioneer_Auto_Playlist.png "Automatic Genre Playlist")

There is special logic for creating "Pure" genre playlists; for example, say you want a "Pure Techno" playlist where the only tracks allowed in it have all genre tags containing the substring "techno". Simply add "techno" to the `GENRE_PLAYLISTS_PURE` list in `config.json`. Then add "Pure Techno" as a playlist in the desired location of your `rekordbox_playlists.json`. After running `djtools --rekordbox_playlists`, the resulting XML will contain this "Pure" genre playlist.

There is additional special logic regarding playlists called "Hip Hop". If a playlist with the name "Hip Hop" appears at the top-level of the playlists structure, then only tracks which have genre tags containing "Hip Hop" or both "Hip Hop" and "R&B" will be added. If the playlist is called "Hip Hop" and does not appear at the top-level of playlists, then only tracks that contain at least one tag which does not contain either "Hip Hop" or "R&B" will be added. The purpose of this is to distinguish between pure hip hop tracks and bass tracks which have hip hop elements.

To trigger the `rekordbox_playlists` module, set `REKORDBOX_PLAYLISTS: true`. Additionally, you can set `REKORDBOX_PLAYLISTS_REMAINDER` to either `folder` or `playlist` to place tracks belonging to tags not specified in `rekordbox_playlists.json` in either an "Other" folder of tag playlists or simply aggregate them all into an "Other" playlist.

Once the operation completes, an XML is generated at `XML_PATH` with the prefix `auto_`. Import your playlist structure from the XML.
