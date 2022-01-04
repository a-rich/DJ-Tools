# Spotify

## Contents
* Overview
* Setup
* Usage

# Overview
The `spotify` package contains modules:
* `playlist_checker`: checks Spotify playlists for tracks that overlap with those already in the beatcloud
* `playlist_builder`: constructs / updates Spotify playlists from subreddit top posts

# Setup
To begin using the `spotify` package, you must create a Spotify API application by following [these instructions](https://developer.spotify.com/documentation/web-api/quick-start/). Once you've registered your application, you must populate the `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and `SPOTIFY_REDIRECT_URI` configuration options in `config.json`.

If using the `playlist_builder` module, you must also create a Reddit API application by following [these instructions](https://rymur.github.io/setup). Once you've registered your application, you must populate the `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, and `REDDIT_USER_AGENT` configuration options in `config.json`. Additionally, `SPOTIFY_USERNAME` must be set to the user who will keep the playlists on their account.

# Usage

## playlist_checker
In order to use the `playlist_checker` module, you must add a `playlist_checker.json` file to the `config` folder. This JSON contains playlist names as keys and Spotify playlist IDs as values (the playlist names don't necessarily have to match the actual names of the Spotify playlists). Then you must add the playlist names you want to check against to the `SPOTIFY_PLAYLISTS_CHECK` configuration option. 

The `SPOTIFY_PLAYLISTS_CHECK_FUZZ_RATIO` configuration option `[0, 100]` sets the minimum Levenshtein similarity between the `Title - Artist` of the Spotify tracks and the file names of tracks in the `beatcloud`.

Triggering the `playlist_checker` module can be done by setting `SPOTIFY_CHECK_PLAYLISTS: true`.

## playlist_builder
In order to use the `playlist_builder` module, you must add a `playlist_builder.json` file to the `config` folder. This JSON contains subreddits as keys and Spotify playlist IDs as values. Unlike `playlist_checker.json`, the JSON keys _MUST_ match the subreddit (case-insensitive). Then you must add the subreddits you want to generate / update paylists for to the `AUTO_PLAYLIST_SUBREDDITS` configuration option.

There are three other relevant configuration options for the `playlist_builder` module. `AUTO_PLAYLIST_TRACK_LIMIT` is the maximum number of tracks in the auto-playlists; the oldest track will be removed when adding a new track exceeds this limit. `AUTO_PLAYLIST_TOP_PERIOD` is the time period for which top posts are considered; `week` is recommended. Should a subreddit top post not contain a direct link to a Spotify track, `AUTO_PLAYLIST_FUZZ_RATIO` `[0, 100]` sets the minimum Levenshtein similarity to add tracks to an auto-playlist when comparing the subreddit post title to a Spotify API search result.

Triggering the `playlist_builder` module can be done by setting `AUTO_PLAYLIST_UPDATE: true`.
