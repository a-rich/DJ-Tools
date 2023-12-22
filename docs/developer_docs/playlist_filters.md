# PlaylistFilters

When creating playlists, the `playlist_builder` calls `filter_tag_playlists` with a configurable list of `PlaylistFilter` implementations:

::: djtools.collection.helpers.filter_tag_playlists
    options:
        show_docstring_description: false
        show_docstring_parameters: false
        show_docstring_returns: false

These `PlaylistFilters` inject custom behavior into the `playlist_builder`. In general, this is done by scanning through a playlist structure and looking for a playlist, or playlists, that match some description and then filter for tracks that match another description.

::: djtools.collection.playlist_filters.PlaylistFilter
    options:
        show_bases: false
        members: false
        show_docstring_description: false

`PlaylistFilter` subclasses must implement two methods:

- `is_filter_playlist`: returns `True` if a given `Playlist` should have the filter applied to its tracks
- `filter_track`: returns `True` if a track should remain in the playlist after applying the filter.

Once a `PlaylistFilter` is implemented, it must be added to the list of supported `COLLECTION_PLAYLIST_FILTERS`:

::: djtools.collection.config.CollectionConfig
    options:
        show_bases: false
        members: false
        show_docstring_description: false


## PlaylistFilter Implementations

The `playlist_filters` module contains the following set of `PlaylistFilter` implementations:
- `HipHopFilter`
- `MinimalDeepTechFilter`
- `TransitionTrackFilter`
- `ComplexTrackFilter`

### HipHopFilter
- Checks to see if a playlist named 'Hip Hop' is a child of a playlist named 'Bass'
- If it is, then tracks in that playlist must have a genre tag besides 'Hip Hop' and 'R&B'
- If it is not, then tracks in that playlist must have only genre tags 'Hip Hop' and 'R&B'

### MinimalDeepTechFilter
- Checks to see if a playlist named 'Minimal Deep Tech' is a child of a playlist named 'Techno' or 'House'
- If it's a child of a 'Techno' playlist, then at least one other genre tag must contain the substring 'techno' (case insensitive)
- If it's a child of a 'House' playlist, then at least one other genre tag must contain the substring 'house'

### ComplexTrackFilter
- Checks to see if the playlist, or a parent playlist, contains the substring 'complex' 
- Filters tracks that contain fewer than a set number of tags (only includes "other" tags, does not include genre tags)
- When instantiated, `ComplexTrackFilter` takes optional arguments for the `minimum_tags_for_complex_track` as well as the list of `exclude_tags` which may not count towards the total number of tags

### TransitionTrackFilter
- Checks to see if the playlist, or a parent playlist, contains the substring 'transition' 
- Checks to see if the playlist contains one, and only one, of the substrings 'genre' or 'tempo'
- Filters tracks that contain a special annotation in their comments field
- The expected annotation must match the following syntax `[ token1 / token2]` where a `token` must be strings if it's a 'genre' transition playlist or numbers if it's a 'tempo' transition playlist
