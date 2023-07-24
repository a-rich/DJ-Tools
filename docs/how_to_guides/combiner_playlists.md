# Combine Playlists with Boolean Algebra

In this guide you will learn how to automatically build playlists based off of powerful boolean algebra expressions that apply set operations to tags, playlists, and other selections of your Collection.

## Prerequisites

* [Rekordbox settings](../tutorials/getting_started/setup.md#rekordbox-settings)
* [Get to Know Your Rekordbox Collection](../conceptual_guides/rekordbox_collection.md)
* [A light review of set theory](https://en.wikipedia.org/wiki/Set_theory#Basic_concepts_and_notation)

## Why combine playlists with boolean algebra?
It may not be commonly known, but Rekordbox already has a very elementary version of this functionality called the "Track Filter":
![alt text](../images/Rekordbox_track_filter.png "Rekordbox Track Filter")

There are many shortcomings with the Track Filter which make it far inferior to the [Combiner][djtools.collection.helpers.build_combiner_playlists]:

1. Portability
    * can only be used on a laptop running Rekordbox (not available on XDJs, CDJs, etc.)
    * can only be used with the master database on a laptop (friends plugging in their devices lose access to this feature)
1. Operands
    * only works on `My Tags`, color, rating, key, and a maximum of 6% range from a single BPM value
1. Operators
    * can only apply `AND` and `OR` logic
    * can only apply logic to `My Tags`
    * can only apply one of these logic operators per grouping of `My Tags`

The `Combiner` solves all these issues in the following ways:

1. Portability
    * generates regular playlists which can be exported to a device for use on any system
1. Operands
    * works on any tag data that `djtools` knows of (e.g. genres, `My Tags`, etc.)
    * includes numerical selector syntax to choose arbitrary rating, BPM, and year values as well as arbitrary ranges of those values
    * includes string selector syntax to choose playlists in your Collection as well as artists, comments, dates added, keys, and record labels
    * any of the string selectors (except for `date`) support wildcard globbing with the `*` character
1. Operators
    * adds a `NOT` operator to take the set difference
    * allows you to apply logic operators to *any* of the operands, not just `My Tags`
    * allows you to construct arbitrarily complex expressions using parentheses to control the order of operations

## Syntax

* logical operators ("AND", "OR", "NOT"):
    - `&`
    - `|`
    - `~`
* string selectors (not case-sensative):
    - `{artist:*Eprom*}`
    - `{comment:*hollaback*}`
    - `{date:2022}`
    - `{date:>2021-10-05}`
    - `{date:<=2020-05}`
    - `{key:7A}`
    - `{label:duploc}`
    - `{playlist: Deep House}`
* numerical selectors:
    - `[0]`
    - `[3-5]`
    - `[80]`
    - `[130-150]`
    - `[1973]`
    - `[2013-2023]`
* grouping:
    - `(`
    - `)`

Let's look at an example playlist to see how the syntax works.

Suppose we want a playlist with tracks that _all have_ the following properties:

- from the years 2000 to 2023
- and have a rating of 5
- and with BPMs in the range 130 to 150

The expression a.k.a. the combiner playlist name will look this:

    [2000-2023] & [5] & [130-150]

Now let's say we want a playlist with tracks that have _any one of_ the following properties:

- have a genre tag called "Jungle"
- or have another tag called "Dark"
- or come from a playlist called "New Years 1999"
- or come from the record label "Dispatch"

The playlist for this set of tracks is expressed like this:

    Jungle | Dark | {playlist: New Years 1999} | {label: Dispatch}

Now let's say we want to create a playlist using the other supported string selectors. We're also going to demonstrate the set difference operator `~` which will remove matching tracks from the resulting playlist. This subset of tracks will _all have_ the following properties:

- have at least one of the artists as "Eprom"
- and have been added to the collection after 2010
- and have the words "absolute banger" in the comments
- and not have a major musical key (using [Camelot notation](https://mixedinkey.com/harmonic-mixing-guide/))

The playlist for these tracks is written like this:

    {artist: *Eprom*} & {date:>2010} & {comment:*absolute banger*} ~ {key:*A}

Finally, let's see how we can create one master playlist from all three of these sub-expressions using groupings to ensure the proper order of operations:

    ([2000-2023] & [5] & [130-150]) |
    (Jungle | Dark | {playlist: New Years 1999} | {label: Dispatch}) |
    ({artist: *Eprom*} & {date:>2010} & {comment:*absolute banger*} ~ {key:*A})
    
I hope you see how powerful the `Combiner` can become when used with a well indexed collection!

## How it's done

1. Configure your desired playlists for the `Combiner` by constructing a boolean algebra expression with the syntax noted above
1. Run the command `--collection-playlists`
1. Import the `PLAYLIST_BUILDER` folder from the generated collection

## Example
As is done in the [Build Playlists From Tags](collection_playlists.md#example) how-to guide, we'll start by looking at some simple expressions configured in the pre-packaged [collection_playlists.yaml](https://github.com/a-rich/DJ-Tools/blob/main/djtools/configs/collection_playlists.yaml), but this time we'll focus only on the `combiner` section:

Note that the examples below are trivial ones designed to get 100% code coverage in unit tests.

![alt text](../images/Rekordbox_playlists_combiner_yaml.png "Collection playlists YAML")

The `combiner` configuration specifies a set of `name` folders with lists of playlists and / or folders inside of them. The leaves of this playlist tree are the actual playlists themselves whose names are boolean algebra expressions that use the syntax noted above to describe how different tags and selectors are to be combined to produce the final playlist of tracks. Valid expressions must contain at least two operands and must have one less operator than there are operands. 

Once you've finalized your playlist configuration, run the following command to build the playlists:

`djtools --collection-playlists`

Now you can import the `PLAYLIST_BUILDER` folder to load these playlists into your Collection:
![alt text](../images/Rekordbox_post_playlists_combiner.png "Generated combiner playlists")