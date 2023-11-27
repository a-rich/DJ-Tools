# Scripts

* `collection`
    - `get_tags_from_spotify`
        * queries Spotify API in order to populate `album`, `label`, and `year` data in a collection
    - `move_tags`
        * moves data around from different fields in a collection; e.g. moving certain tags from `Comments` to `Genre` or moving a particular tag in `Comments` to the front of that field
    - `remove_tags_from_comments`
        * filters out undesirable tags from the `Comments` field
    - `sort_tags`
        * sort non-genre tags to be in alphabetical order
    - `tracks_outside_playlists`
        * identifies all tracks that do not appear in a given playlist or folder of playlists -- "dangling" tracks will be aggregated into a new playlist
    - `update_collection`
        * copies track data from a source collection to a target collection (i.e. updating a master collection with new tracks)
    - `user_vibe_analysis`
        * generates histograms for users' `Vibe` tag distributions
* `repair`
    - `move_music_new_structure`
        * restructures the old audio file hierarchy (genres at the top-leve) to the new one (users at the top-level)
    - `normalize_audio`
        * normalizes the amplitude and bitrate of tracks in a collection
    - `rename_files`
        * assists an onboarding user with migrating their existing collection to a folder compatible folder structure
    - `swap_title_artist`
        * repairs files in the beatcloud that are named `Artist - Title` instead of `Title - Artist`
        * can also fix the same tracks in an XML if they were already imported  -- useful for greatly speeding up the process of relocating the repaired tracks without having to reimport and, therefore, losing all the associated Rekordbox data
* `testing`
    - `parse_pytest_output`
        * analyzes the timing of unit tests and fixtures
