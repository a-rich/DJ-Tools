# Check the Beatcloud for Tracks in Spotify Playlists or Local Directories

In this guide you will learn how to compare the contents of one or more Spotify playlists and / or one or more local directories with the contents of the Beatcloud in order to identify redundancies.

## Prerequisites

* [Setup Object Storage For Syncing Files](setup_object_storage.md)
* [Setup API access for Spotify and Reddit](reddit_spotify_api_access.md)

## Why check the Beatcloud against Spotify playlists and / or local directories?
When managing a shared collection of tracks across multiple users, it can become difficult to ensure that the same tracks aren't being added to the Beatcloud again and again.

Some users, such as myself, use Spotify playlists to discover new tracks and incubate on them to determine if they're worth incorporating into my collection. I can save myself the effort of considering tracks if I can determine ahead of time that they already exist in the Beatcloud.

Once tracks are acquired, it may be necessary to compare a location on my computer containing those tracks with the Beatcloud to be sure they don't exist prior to running `--upload-music`.

## How it's done
1. If using the `check_tracks_spotify_playlists` option, ensure that the playlist names configured for that option exist as `playlist name: playlist ID` mappings in `spotify_playlists.yaml`
    - you'll have to add these manually (grab the playlist ID from the URL when opening the playlist in the browser or from the link copied when sharing a playlist in the app)
    - playlist names don't necessarily have to match the actual name of the playlist...they're just used to lookup the IDs when configuring `utils` options
1. Configure `check_tracks_spotify_playlists` and / or `local_dirs` to contain the playlist names and / or absolute paths, respectively, to the tracks you want to compare with the Beatcloud
1. If your files are stored in the Beatcloud using the format `Artist1, Artist2 - Title (Artist2 Remix)` instead of the default `Title (Artist2 Remix) - Artist1, Artist2`, make sure you set `artist_first` to `true` (see [Configuration](../tutorials/getting_started/configuration.md#base-config) for more detail)
    * Note that you can temporarily set `artist_first` to `true` when running with `local_dirs`, even if your Beatcloud tracks are *not* stored in the `artist_first` format, in order to compare against local tracks that *do* adhere to the `artist_first` format
1. Run the command `djtools --check-tracks`

## Example
To begin, make sure the Spotify playlists you're targeting with this feature have entries in `spotify_playlists.yaml`:
```
Maybe Download: 7zh4Lru54fGrBUwgOU1G6f
Todays Beats: 5R90HSqiP6oIY8jPFgki4h
```

Configure `check_tracks_spotify_playlists` and `local_dirs` to so they point to the playlists and local directories you want to use for comparison:
```
check_tracks_spotify_playlists:
    - Todays Beats
    - Maybe Download
local_dirs:
    - /Users/aweeeezy/Downloads/New Music
```

After running the command, I can determine by the console output that I have no overlapping tracks between my local directory and the Beatcloud, but I do have a track in my "Today's Beats" Spotify playlist that matches 100% with "Zodd's Hunger - Noer the Boy" in my Beatcloud instance:
```
check_tracks
Got 7 track from Spotify playlist "Maybe Download"
Got 9 tracks from Spotify playlist "Todays Beats"
Got 16 tracks from Spotify in total
Got 22 files under local directories
Got 4025 tracks from the beatcloud
Matching new and Beatcloud tracks: 100%|███████████████████████████████████████████████████████████████████████████████████████████| 132726/132726 [00:00<00:00, 751116.76it/s]
Spotify Playlist Tracks / Beatcloud Matches: 1
Todays Beats:
   100: Zodd's Hunger - Noer the Boy | Zodd's Hunger - Noer the Boy
Matching new and Beatcloud tracks: 100%|█████████████████████████████████████████████████████████████████████████████████████████████| 88484/88484 [00:00<00:00, 882570.40it/s]
Local Directory Tracks / Beatcloud Matches: 0
```
