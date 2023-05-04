# Scripts

* repair
    - swap_title_artist
        * used to repair files in the beatcloud that are named `Artist - Title` instead of `Title - Artist`
        * can also fix the same tracks in an XML if they were already imported  -- useful for greatly speeding up the process of relocating the repaired tracks without having to reimport and, therefore, losing all the associated Rekordbox data
    - move_music_new_structure
        * used to restructure the old audio file hierarcy (genres at the top-leve) to the new one (users at the top-level)
* xml
    - tracks_outside_playlists
        * used to identify all tracks that do not appear in a given playlist or folder of playlists -- "dangling" tracks will be aggregated into a new playlist
    - move_genre_tags
        * take a set of tags encoded in the `Comments` field and relocate them to the `Genre` field
* deprecated
    - spotify_analysis
        * old spotify analysis with additional (not useful?) functionality that was not ported to DJ Tools
* testing
    - parse_pytest_output
        * used to analyze the timing of unit tests and fixtures
