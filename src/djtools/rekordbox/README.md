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

The `rekordbox_playlist_builder` module requires that you utilize "genre" tags and / or "My Tags" tags for tracks in your Collection. It's also required that `XML_PATH` exists as well as a `rekordbox_playlists.json` in your config folder. Additionally, if any of your Collection's tracks have multiple genres specified in the genre tag field, they must be delimited with a `/` character.

# Usage

## randomize_tracks
To trigger the `randomize_tracks` module, set `RANDOMIZE_TRACKS: true`. Once the operation has completed, you'll need to open Rekordbox and reimport the `AUTO_RANDOMIZE` playlist containing the set of tracks with updated `TrackNumber` fields.

## rekordbox_playlist_builder 
To trigger the `rekordbox_playlists` module, set `REKORDBOX_PLAYLISTS: true`. Once the operation completes, an XML is generated at `XML_PATH` with the prefix `auto_`. Import your auto-playlist structure from this XML.

For the `rekordbox_playlist_builder` module to run, there must be a `rekordbox_playlists.json` in your config folder. This JSON must be a dictionary with class names of subclass of `TagParser` as keys (currently only `GenreTagParser`, `MyTagParser`, and `Combiner` are supported) and values as dictionaries with the following keys: `name` for the name of your playlist folder and `playlists` with a list of values which can be either strings (playlist names) or dictionaries (subfolders with more playlists / subfolders inside of them).

### In general
Tags are case-sensitive and must match a single tag (unless using wildcards in the "Combiner" playlists).

Any subfolder will implicitly have an `All <subfolder name>` playlist to collect all tracks that are inserted into playlists belonging to that subfolder. This operation is recursive ignoring the top-level folder.

Additionally, you can set `REKORDBOX_PLAYLISTS_REMAINDER` to either `folder` or `playlist` to place tracks belonging to tags not specified in `rekordbox_playlists.json` in either an "Other" folder of remainder tag playlists or an "Other" playlist containing all the tracks with remainder tags. You can insert a folder called `"_ignore"` anywhere in the structure except at the top-level and add a list of tags to ignore in the "playlists" key. Tracks with these tags will not be inserted into the "Other" folder / playlist.

### More on the "GenreTagParser"
There is special logic for creating "Pure" genre playlists; for example, say you want a "Pure Techno" playlist where the only tracks allowed in it have all genre tags containing the substring "techno". Simply add "techno" to the `GENRE_PLAYLISTS_PURE` list in `config.json`. Then add "Pure Techno" as a playlist in the desired location of your `rekordbox_playlists.json`.

There is additional special logic regarding playlists called "Hip Hop". If a playlist with the name "Hip Hop" appears at the top-level of the playlists structure, then only tracks which have genre tags containing "Hip Hop" or both "Hip Hop" and "R&B" will be added. If the playlist is called "Hip Hop" and does not appear at the top-level of playlists, then only tracks that contain at least one tag which does not contain either "Hip Hop" or "R&B" will be added. The purpose of this is to distinguish between pure hip hop tracks and bass tracks which have hip hop elements.

### More on the "Combiner"
Unlike the other auto-playlists, the "Combiner" config does not support the `"_ignore"` or `All <subfolder name>` features as they are not releveant. Additionally, "playlists" must be a flat list of boolean algebra expressions containing only valid tags ("genre" or "My Tags") and these valid characters for boolean algebra:

{ `&`, `|`, `~`, `(`, `)`, `*` `{`, `}`, `[`, `]`}

These symbols, respectively, are for applying `AND`, `OR`, `NOT`, `OPEN SUBEXPRESSION`, `CLOSE SUBEXPRESSION`, `WILDCARD`, `PLAYLIST SELECTION`, and `BPM / RATING SELECTION`.

A `WILDCARD` is used to catch multiple genres; for example, if you want a playlist with all house genres except for Bass House, this can be expressed with `*HOUSE ~ Bass House`.

`PLAYLIST SELECTION` is done by enclosing the exact name (case-sensative) of a playlist in curly braces like this: `{My Playlist}`.

`BPM / RATING SELECTION` is done by enclosing a BPM and / or rating selections in square brackets. Single BPM / rating selections are supported as are ranges by separting values with a dash. Multiple ranges and / or single values are separated by a comma. Numbers between 0 and 5 inclusive are interpreted as ratings while numbers greater than 5 are interpreted as BPM. 

Here is an example selector:

`[1-3, 5, 138, 142-147, 80-90, 95]`. 

This will select tracks that have a rating between 1 and 3 inclusive and a rating of 5. It will also select tracks with a BPM of 138, 95, and between 142 and 147, as well as between 80 and 90. Note that, when being considered for selection, track BPMs are rounded to the nearest whole number.

More examples of valid boolean algebra expression to be used with the "Combiner" can be seen below.


Here is an example `rekordbox_playlists.json`:
```
{
    "Combiner": {
        "name": "Combinations",
        "playlists": [
            "(Hard Techno & Acid Techno) | Minimal Techno",
            "Minimal House | Techno",
            "(Jungle | Breaks & Techno) | (Garage ~ Tech House)",
            "Wave ~ Trap | Uplifting",
            "*House ~ Bass House",
            "{All DnB} & Uplifting",
            "{All Bass} & [137-143]",
            "Dark & [5]"
        ]
    },
    "MyTagParser": {
        "name": "My Tags",
        "playlists": [
            {
                "name": "_ignore",
                "playlists": [
                    "Vocal",
                    "Wave"
                ]
            },
            "Dark",
            "Uplifiting"
        ]
    },
    "GenreTagParser": {
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
The above structure generates a set of auto-playlists like this:

![alt text](https://raw.githubusercontent.com/a-rich/DJ-Tools/2.3.0/images/Pioneer_Auto_Playlist.png "Automatic Genre Playlist")