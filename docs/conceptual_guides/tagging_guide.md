# Tagging Guide

In this guide, I'll be offering opinions, tips, and best-practices for tagging your collection.

Having indexed and re-indexed my collection of thousands of tracks several times already, there are a handful of things I wish I knew from the beginning that could have saved me a few passes through my library.

I'll begin with three general tips that should be applicable regardless of what types of tagging you're doing.
I'll then go over tips grouped by the more specific types of tags such as genres, ratings, and "other" tags.


## General Tips

### Tip #1: Know what metadata fields are available to you
Before embarking on a potentially multi-month journey to index your collection, make sure you're aware of all the ways you can attach information to your tracks.
The worst time to realize you could have been using a particular field to encode information is after you've finished applying a process to your entire collection.

Look over each column and determine if you have a purpose (or repurpose) for that information. In, for example, the Rekordbox library view, all the available fields can have their visibility toggled by right-clicking on the column headers.

Build a plan for what information is valuable to you both while preparing and executing mixes and keep this plan in mind while applying your processes.
Remember that some information may not always be available to you.
For example, I once applied a hot cue schema to all my tracks before realizing that older CDJs only have access to the first three hot cues.
I then had to go through all my tracks and reorder the hot cues so the three most practical cue points filled the A, B, and C hot cue positions.

Look through the full set of preferences for your library management software and make sure you're maximizing your ability to capture useful information.
In Rekordbox, if you want `djtools` to be able to build playlists from your `My Tags` data, or if you want to be able to search `My Tag` data on CDJs, you must enable the setting `Add "My Tags" to the "Comments"`.
Please see the [setup guide](../tutorials/getting_started/setup.md#writing-my-tag-data-to-the-comments-field) for more info.

`NOTE:`
You should be applying your findings from `Tip #1` while executing on `Tip #2` and `Tip #3`.
By incubating on your plans for tagging while scanning through your collection, you may find ways to improve those plans before you even start tagging.

### Tip #2: Prune your library
Attempting to apply all your tags to your entire collection in one shot may sound like a good plan, but it's likely going to lead to you needing to re-tag your collection for one reason or another.
You also might find that some types of tagging processes are much easier to do after you've already completed another tagging process.

Before tagging, I recommend doing a quick pass through your whole collection and copy tracks that you may want to consider deleting into a `DELETE` playlist.
Even if you don't end up deleting anything, it can be a useful exercise to critically assess the value each track has.
If you do end up deleting stuff, then you'll have an easier time applying tags.

There are multiple reasons why you may want to mark a track for deletion:

- track duration is too short to be practical -- yeah it's dope, but are you really gonna mix that 40 second beat?
- track is well outside your mixing style -- I love Pink Floyd too, but you'll probably never mix Comfortably Numb into your DnB sets
- that low quality rip from YouTube may have seemed like a good addition while you were obsessed with having that track, but now it just sounds horrible

### Tip #3: Identify "golden tracks"
While doing this preliminary pruning scan, also copy exceptional tracks into a `Golden Tracks` playlist.
Think of this playlist as a testbed where you can try out your schemas on a batch of diverse tracks that are practical and you enjoy mixing.
Detecting a deficiency in your schemas early on in this playlist will save you a bunch of time. 

For your `Golden Tracks` playlist to be effective for this purpose, it must be representative of your library, meaning it should have enough samples from each of the different corners of your collection.
I recommend adding songs that you either have an exceptional fondness of, are relatively unique in style and character, or you feel contribute significantly towards defining your mixing style.
Don't confuse this as a `My Favorites` playlist -- your taste in music changes over time.
The most critical property of `Golden Tracks` is that it's diverse!
Ideally, the contents of the playlist will force you to increase the scope of your schemas.

Of course, what your `Golden Tracks` playlist looks like depends on multiple factors such as the maturity, size, and diversity of your collection.
If you have a massive collection comprised of many different styles, your `Golden Tracks` playlist should capture those styles and it might be a large playlist with hundreds of tracks.
Conversely, if your have a small and very homogenous library, your `Golden Tracks` might as well be your entire library. But, if this is the case, you're probably not interested in tagging your collection anyway.

## Specific Tagging Strategies

### Genre tags

#### Find a useful middle-ground regarding the specificity of your genre tags
You don't want your genre tags to be too specific or else you risk them loosing their value.
If you're able to describe many of your tracks with a single genre tag, your genres are too specific.
You'll end up with a bunch of genre playlists that have three tracks in them causing you to waste a bunch of time during the mix moving through different playlists.

On the other hand, if your genre tags are too broad, you'll have genre playlists with many tracks that don't belong near each other which will lead to you wasting time previewing tracks that don't fit in the mix.

You will definitely have tracks that you feel you can't distinguish with the genres you have.
Don't forget that you can use "other" tags too.
Trying to describe all the variance in your tracks with only genre tags is a mistake!
Genre tags should be used for establishing macro groups in your library, not for completely capturing all the characteristics of each and every track.

`NOTE:`
If you're a Rekordbox user, for `djtools` to be able to build playlists using genre tags, tracks with multiple genres must have those tags separated by forward slashes.

#### Don't let perfect get in the way of good
It's easy to feel discouraged when trying to determine what genres you should use in your collection.
Remember, this is an iterative learning process and you will almost certainly discover as you go what to call tracks you've collected.
Again, this is why you want to have a `Golden Tracks` playlist so you can try out your ideas before you commit to them completely.

Inevitably you'll find you made judgement errors when tagging and will have to go back and fix them.
I finished tagging the genres of my collection years ago and I'm still occasionally finding tracks in playlists that feel out of place.
That's the beauty of the playlist builder in `djtools`!
Whenever you find an out of place track, correcting it is as easy as editing the tags for the track before rebuilding your playlists.

### "Other" tags
"Other" tags are any custom tags that don't fall under a pre-defined field (like "artist", "genre", etc.). In Rekordbox, these are called `My Tags`. 

`NOTE:`
For Rekordbox users' `My Tags` to be readable by `djtools` they must enable `Add "My Tags" to the "Comments"`.
Don't worry, these setting works retroactively, so you don't need to worry about wasted effort if you've already tagged tracks without this setting enabled.
Please see the [setup guide](../tutorials/getting_started/setup.md#writing-my-tag-data-to-the-comments-field) for more info.

Because "other" tags are user-defined and highly subjective, there's not a lot I can say about how they should be designed in general, but I can offer some insight about the specific tags I'm using and my experience establishing these as my tags.

The group of `My Tags` that I've found the most useful are my "Vibes" tags.
As the name suggests, these describe the prominent vibes of a track.
Every track in my collection can be described by at least one of these but are often described by some combination of them.
Some of the most vibe-rich tracks in my collection are described by as many as 8 of these:

  - Aggro, Atmospheric, Bounce, Dark, Deep, Gangsta, Groovy, Heavy, Hypnotic, Melancholy, Melodic, Rave, Strange, Uplifting

In terms of my process for establishing the "Vibes" tags, I experienced issues both with having too many tags and also not having enough tags.
I would recommend to anyone doing something similar to error on the side having too many tags.
It's very easy to find tracks with tags you want to get rid of and re-tag that subset.
Comparatively, it's very difficult to find the tracks that ought to have a new tag you're wanting to introduce after the fact.
This likely will lead to the need to again go through your entire collection to determine if a new tag is applicable.

### Ratings as Energy Levels
`djtools` parses the rating field as integers from `0` through `5` and the playlist builder permits users to express these as numerical selectors.
In effect, you can target sections of your library by their energy level.
For example, you can make a folder of House tracks grouped by low, medium, and high energy levels:
```
    - name: House Energies
    playlists:
        - name: Low
          tag_content: "House & [1-2]"
        - name: Medium
          tag_content: "House & [3]"
        - name: High
          tag_content: "House & [4-5]"
```

On my first attempt at encoding energy levels for my tracks, I made the mistake of scaling the energy level using my entire collection.
As a result, tracks in genres that have higher energy levels (think "Brostep" or "Neurofunk") would all be 4 or 5 stars while tracks in genres that have lower energy levels (think "Ambient" or "Deep House") would all have 1 or 2 stars.

On my second attempt at encoding energy levels, I had much more success using the genre tags to normalize energy levels.
So the average "Deep House" track has 3 stars and the average "Brostep" track also has 3 stars.
This way, when mixing, I can use the context of what style of music I'm mixing to interpret the energy level relative to other tracks that are likely to be mixed together.

## Footnotes

I decided to cover genre, other, and rating tags here because they are the most useful fields for me.

Keep the points made here in mind regardless of which fields you use for encoding information because tagging is inherently a time-consuming exercise and I believe these tips will help reduce wasted effort.

Also, please consult the documentation on building [tag playlists](../how_to_guides/collection_playlists.md) and [Combiner playlists](../how_to_guides/combiner_playlists.md) to better understand how `djtools` uses your tracks' tags to automatically build playlists.
It may help you in determining what schemas you want to apply to your library.
