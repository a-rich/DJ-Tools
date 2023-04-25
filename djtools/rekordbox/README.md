# Playlist Builder

## Contents
* Overview
* Setup
* Usage

# Overview
The `playlist_builder` package contains modules:
* `config`: the configuration object for the `rekordbox` package
* `copy_playlists`: copies audio files for tracks within a set of playlists to a new location and writes a new XML with these updated paths
* `helpers`: contains helper classes and functions for the other modules of this package
* `playlist_builder`: constructs rekordbox playlists using tags in a Collection and a defined playlist structure in `rekordbox_playlists.yaml`
* `randomize_playlists`: writes sequential numbers to Rekordbox tags of shuffled tracks in playlists to emulate playlist shuffling
* `tag_parsers`: the `TagParser` abstract base class and its implementations used by the `playlist_builder`

# Setup
The `copy_playlists` module requires that the playlists in `COPY_PLAYLISTS` exist inside `XML_PATH`, and `COPY_PLAYLISTS_DESTINATION` is set to a valid path (or not set in which case the current directory will be used).

The `playlist_builder` module requires that you utilize "genre" and / or "My Tags" tags for tracks in your Collection. You can actually use just the playlist, BPM, and rating selectors in the `Combiner` playlists, but you will be missing out on a lot of the features of this module if you don't also tag your library. It's also required that `XML_PATH` exists as well as a `rekordbox_playlists.yaml` in your config folder. Additionally, if any of your Collection's tracks have multiple genres specified in the genre tag field, they must be delimited with a `/` character. This is also the default delimiter for "My Tags" data written to the Comments field.

The `randomize_playlists` module requires that `XML_PATH` exists. Additionally, playlists in `RANDOMIZE_PLAYLISTS` must exist inside `XML_PATH`.

# Usage
## copy_playlists
To trigger the `copy_playlists` module, set `COPY_PLAYLISTS` to one or more valid playlists in `XML_PATH` and ensure `COPY_PLAYLISTS` is set.

## playlist_builder 
To trigger the `rekordbox_playlists` module, set `REKORDBOX_PLAYLISTS: true`. Once the operation completes, an XML is generated at `XML_PATH` with the prefix `auto_`. Import your auto-playlist structure from this XML.

For the `playlist_builder` module to run, there must be a `rekordbox_playlists.yaml` in your config folder. This YAML must be a dictionary with the class names within `tag_parsers.py` as keys (currently only `GenreTagParser`, `MyTagParser`, and `Combiner` are supported) and values as dictionaries with the following keys: `name` for the name of your playlist folder and `playlists` with a list of values which can be either strings (playlist names) or dictionaries (subfolders with more playlists / subfolders inside of them). `NOTE`: the `Combiner` playlist structure must be a flat list of playlists, no nested folders are allowed.

### In general
Tags are case-sensitive and must match a single tag (unless using wildcards in the `Combiner` playlists).

Any subfolder will implicitly have an `All <subfolder name>` playlist to collect all tracks that are inserted into playlists belonging to that subfolder. This operation is recursive ignoring the top-level folder. `NOTE`: this does not apply to `Combiner` playlists as they are provided as a flat list of playlists without any folders.

Additionally, you can set `REKORDBOX_PLAYLISTS_REMAINDER` to either `folder` or `playlist` to place tracks belonging to tags not specified in `rekordbox_playlists.yaml` in either an "Other" folder of remainder tag playlists or an "Other" playlist containing all the tracks with remainder tags. You can insert a folder called `"_ignore"` anywhere in the structure except at the top-level and add a list of tags to ignore in the "playlists" key. Tracks with these tags will not be inserted into the "Other" folder / playlist. `NOTE`: this does not apply to `Combiner` playlists as they are composites of existing tags i.e. the remainders are already capture in the "Other" structures for the `TagParser` playlists.

### More on the "GenreTagParser"
There is special logic for creating "Pure" genre playlists; for example, say you want a "Pure Techno" playlist where the only tracks allowed in it have all genre tags containing the substring "techno". Simply add "techno" to the `PURE_GENRE_PLAYLISTS` list in `config.yaml`. Then add "Pure Techno" as a playlist in the desired location of your `rekordbox_playlists.yaml`.

There is additional special logic regarding playlists called "Hip Hop". If a playlist with the name "Hip Hop" appears at the top-level of a playlist folder with the name "Genres", then only tracks which have genre tags containing "Hip Hop" or both "Hip Hop" and "R&B" will be added. If the playlist is called "Hip Hop" and does not appear at the top-level of playlists, then only tracks that contain at least one tag which does not contain either "Hip Hop" or "R&B" will be added. The purpose of this is to distinguish between traditional hip hop tracks and other tracks which have strong hip hop elements but are not traditional hip hop tracks.

### More on the "Combiner"
Unlike the other auto-playlists, the "Combiner" config does not support the `_ignore`, `Other`, or `All <subfolder name>` features that the `TagParser` based playlist do because these features are not relevant for the `Combiner`. Additionally, "playlists" must be a flat list (not nested folders) of boolean algebra expressions containing only valid tags ("genre" or "My Tags") and these valid characters for boolean algebra:

{ `&`, `|`, `~`, `*`, `(`, `)`, `{`, `}`, `[`, `]`}

These symbols, respectively, are for applying `AND`, `OR`, `NOT`, `WILDCARD`, `SUBEXPRESSION`, `PLAYLIST SELECTION`, and `BPM / RATING SELECTION`.

A `WILDCARD` is used to catch multiple genres; for example, if you want a playlist with all house genres except for Bass House, this can be expressed with `*HOUSE ~ Bass House`.

`PLAYLIST SELECTION` is done by enclosing the name (case-sensative) of a playlist in curly braces like this: `{My Playlist}`.

`BPM / RATING SELECTION` is done by enclosing a BPM and / or rating selections in square brackets. Single BPM / rating selections are supported as are ranges by separting values with a dash. Multiple ranges and / or single values are separated by a comma. Numbers between 0 and 5 inclusive are interpreted as ratings while numbers greater than 5 are interpreted as BPM. 

Here is an example selector:

`[1-3, 5, 138, 95, 142-147, 80-90]`. 

This will select tracks that have a rating between 1 and 3 inclusive and a rating of 5. It will also select tracks with a BPM of 138, 95, and between 142 and 147, as well as between 80 and 90. Note that, when being considered for selection, track BPMs are rounded to the nearest whole number.

More examples of valid boolean algebra expression to be used with the "Combiner" can be seen below.

Here is an example `rekordbox_playlists.yaml`:
```
Combiner:
  name: Combinations
  playlists:
    - (Hard Techno & Acid Techno) | Minimal Techno
    - Minimal House | Techno
    - (Jungle | Breaks & Techno) | (Garage ~ Tech House)
    - Wave ~ Trap | Uplifting
    - "*House ~ Bass House"
    - "{All DnB} & Uplifting"
    - "{All Bass} & [137-143]"
    - Dark & [5]
GenreTagParser:
  name: Genres
  playlists:
    - name: _ignore
      playlists:
        - Psychedelic Rock
        - Soul
    - name: Bass
      playlists:
        - name: Breaks
          playlists:
            - Breakstep
            - Neurobreaks
        - name: Hip Hop Beats
          playlists:
            - Halftime
            - Hip Hop
        - Space Bass
        - name: "[___] Step"
          playlists:
            - Breakstep
            - Dubstep
    - Hip Hop
    - name: Techno
      playlists:
        - Pure Techno
        - Hard Techno
MyTagParser:
  name: My Tags
  playlists:
    - name: _ignore
      playlists:
        - Vocal
        - Wave
    - Dark
    - Uplifting 
```
The above structure generates a set of auto-playlists like this:

![alt text](https://raw.githubusercontent.com/a-rich/DJ-Tools/main/images/Pioneer_Auto_Playlist.png "Automatic Genre Playlist")

## randomize_playlists
To trigger the `randomize_playlists` module, set `RANDOMIZE_PLAYLISTS` to a list of playlists that exist in `XML_PATH`. Once the operation has completed, you'll need to open Rekordbox and reimport the `AUTO_RANDOMIZE` playlist containing the set of tracks with updated `TrackNumber` fields.