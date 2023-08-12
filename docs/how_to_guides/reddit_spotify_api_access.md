# Setup Spotify & Reddit API Access

In this guide you will learn how to setup authorization to the Spotify and Reddit APIs in order to use the following features:

* [Checking for track overlap between the Beatcloud and Spotify playlists](check_beatcloud.md)
* [Creating Spotify playlists from Reddit submissions](spotify_playlist_from_reddit.md)
* [Creating Spotify playlists from other Beatcloud users' uploads](spotify_playlist_from_upload.md)
* [Syncing tracks from a Spotify playlist](sync_spotify.md)

## How it's done

1. Setup access to the Spotify API by following their [official documentation](https://developer.spotify.com/documentation/web-api)
1. Setup access to the Reddit API (only needed if [Creating Spotify Playlists From Reddit Submissions](spotify_playlist_from_reddit.md)) -- take a look at [reddit.com/wiki/api](https://www.reddit.com/wiki/api) or follow PRAW's [Quick Start guide](https://praw.readthedocs.io/en/stable/getting_started/authentication.html#oauth)
1. Populate the following list of config options:
    - `REDDIT_CLIENT_ID`
    - `REDDIT_CLIENT_SECRET`
    - `REDDIT_USER_AGENT`
    - `SPOTIFY_CLIENT_ID`
    - `SPOTIFY_CLIENT_SECRET`
    - `SPOTIFY_REDIRECT_URI`
    - `SPOTIFY_USERNAME`
