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
    - copy_tracks
        * copy audio files from a given playlist and write a new XML with these paths
        * useful if you want to create a backup for a specific playlist or if you want to colocate tracks from across your Collection when mixing on a non-Pioneer setup
* deprecated
    - spotify_analysis
        * old spotify analysis with additional (not useful?) functionality that was not ported to DJ Tools
