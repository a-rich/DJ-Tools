# Scripts

* repair
    - swap_title_artist:
        * used to repair files in the beatcloud that are named `Artist - Title` instead of `Title - Artist`
        * can also fix the same tracks in an XML if they were already imported  -- useful for greatly speeding up the process of relocating the repaired tracks without having to reimport and, therefore, losing all the associated Rekordbox data
* xml
    - tracks_outside_playlists
        * used to identify all tracks that do not appear in a given playlist or folder of playlists -- "dangling" tracks will be aggregated into a new playlist
* deprecated
    - spotify_analysis
        * old spotify analysis with additional (not useful?) functionality that was not ported to DJ Tools
