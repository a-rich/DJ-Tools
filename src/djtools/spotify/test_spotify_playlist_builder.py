import asyncio
from unittest import mock

import pytest

from djtools.spotify.spotify_playlist_builder import (
    async_update_auto_playlists,
    build_new_playlist,
    filter_results,
    filter_tracks,
    fuzzy_match,
    get_subreddit_posts,
    parse_title,
    process,
    track_name_too_similar,
    update_auto_playlists,
    update_existing_playlist,
)
from test_data import MockOpen


pytest_plugins = [
    "test_data",
]


async def aiter(obj, num_subs):
    for i in range(num_subs):
        yield obj
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "playlist_subreddits",
    [[], [{"name": "jungle", "type": "hot", "period": "week", "limit": 50}]],
)
@pytest.mark.parametrize("got_playlist_ids", [True, False])
@pytest.mark.parametrize("got_tracks", [True, False])
@mock.patch("os.path.exists", return_value=True)
@mock.patch(
    "djtools.spotify.spotify_playlist_builder.update_existing_playlist",
    return_value={
        "name": "test_playlist",
        "external_urls": {"spotify": "https://test-url.com"},
        "id": "test-id",
    },
)
@mock.patch(
    "djtools.spotify.spotify_playlist_builder.build_new_playlist",
    return_value={
        "name": "test_playlist",
        "external_urls": {"spotify": "https://test-url.com"},
        "id": "test-id",
    },
)
@mock.patch(
    "djtools.spotify.spotify_playlist_builder.get_subreddit_posts",
    return_value=[
        [("track-id", "track name")],
        {"name": "jungle", "type": "hot", "period": "week", "limit": 50},
    ],
)
@mock.patch("djtools.spotify.spotify_playlist_builder.spotipy.Spotify")
async def test_async_update_auto_playlists(
    mock_spotify,
    mock_get_subreddit_posts,
    mock_build_new_playlist,
    mock_update_existing_playlist,
    mock_os_path_exists,
    got_tracks,
    got_playlist_ids,
    playlist_subreddits,
    test_config,
):
    if not got_tracks:
        mock_get_subreddit_posts.return_value[0] = []
    test_config["SPOTIFY_CLIENT_ID"] = "test_client_id"
    test_config["SPOTIFY_CLIENT_SECRET"] = "test_client_secret"
    test_config["SPOTIFY_REDIRECT_URI"] = "test_redirect_uri"
    test_config["AUTO_PLAYLIST_SUBREDDITS"] = playlist_subreddits
    with mock.patch(
        "builtins.open",
        MockOpen(
            files=["playlist_builder.json", ".praw.cache"],
            content='{"jungle": "some-id"}' if got_playlist_ids else "{}",
        ).open
    ):
        await async_update_auto_playlists(test_config)


@pytest.mark.asyncio
@mock.patch(
    "djtools.spotify.spotify_playlist_builder.get_subreddit_posts",
    return_value=(
        [("track-id", "track name")],
        {"name": "jungle", "type": "hot", "period": "week", "limit": 50},
    ),
)
@mock.patch("djtools.spotify.spotify_playlist_builder.spotipy.Spotify")
async def test_async_update_auto_playlists_missing_spotify_username(
    mock_spotify,
    mock_get_subreddit_posts,
    test_config,
):
    test_config["SPOTIFY_CLIENT_ID"] = "test_client_id"
    test_config["SPOTIFY_CLIENT_SECRET"] = "test_client_secret"
    test_config["SPOTIFY_REDIRECT_URI"] = "test_redirect_uri"
    test_config["AUTO_PLAYLIST_SUBREDDITS"] = [
        {"name": "jungle", "type": "hot", "period": "week", "limit": 50}
    ]
    del test_config["SPOTIFY_USERNAME"]
    with pytest.raises(
        KeyError,
        match="Building a new playlist in the spotify_playlist_builder "
            "module requires the config option SPOTIFY_USERNAME"
    ):
        await async_update_auto_playlists(test_config)


@pytest.mark.asyncio
async def test_async_update_auto_playlists_missing_playlists(test_config, caplog):
    caplog.set_level("ERROR")
    test_config["AUTO_PLAYLIST_SUBREDDITS"] = ""
    ret = await async_update_auto_playlists(test_config)
    assert not ret
    assert caplog.records[0].message == (
        "Using the spotify_playlist_builder module requires the config "
        "option AUTO_PLAYLIST_SUBREDDITS"
    )


@pytest.mark.asyncio
async def test_async_update_auto_playlists_handles_missing_spotify_configs(
    test_config
):
    del test_config["SPOTIFY_CLIENT_ID"]
    test_config["AUTO_PLAYLIST_SUBREDDITS"] = ["playlist"]
    with pytest.raises(
        KeyError,
        match="Using the spotify_playlist_builder module requires the "
            "following config options: SPOTIFY_CLIENT_ID, "
            "SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI",
    ):
        await async_update_auto_playlists(test_config)
        

@pytest.mark.asyncio
async def test_async_update_auto_playlists_handles_bad_spotify_configs(test_config):
    test_config["AUTO_PLAYLIST_SUBREDDITS"] = ["playlist"]
    with pytest.raises(
        Exception,
        match="Failed to instantiate the Spotify client",
    ):
        await async_update_auto_playlists(test_config)


@pytest.mark.asyncio
@mock.patch("djtools.spotify.spotify_playlist_builder.spotipy.Spotify")
async def test_async_update_auto_playlists_handles_missing_reddit_configs(
    mock_spotify,
    test_config,
):
    del test_config["REDDIT_CLIENT_ID"]
    test_config["SPOTIFY_CLIENT_ID"] = "test_client_id"
    test_config["SPOTIFY_CLIENT_SECRET"] = "test_client_secret"
    test_config["SPOTIFY_REDIRECT_URI"] = "test_redirect_uri"
    test_config["AUTO_PLAYLIST_SUBREDDITS"] = ["playlist"]
    with pytest.raises(
        KeyError,
        match="Using the spotify_playlist_builder module requires the "
            "following config options: REDDIT_CLIENT_ID, "
            "REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT"
    ):
        await async_update_auto_playlists(test_config)


@mock.patch(
    "djtools.spotify.spotify_playlist_checker.spotipy.Spotify."
    "playlist_add_items",
    return_value=(),
)
@mock.patch(
    "djtools.spotify.spotify_playlist_checker.spotipy.Spotify."
    "user_playlist_create",
    return_value={"id": "test_id"},
)
@mock.patch(
    "djtools.spotify.spotify_playlist_checker.spotipy.Spotify",
)
def test_build_new_playlist(
    mock_spotify,
    mock_spotify_user_playlist_create,
    mock_spotify_playlist_add_items,
):
    mock_spotify.user_playlist_create.return_value = (
        mock_spotify_user_playlist_create.return_value
    )
    mock_spotify.playlist_add_items.return_value = (
        mock_spotify_playlist_add_items.return_value
    )
    new_tracks = [("test_id", "track title - artist name")]
    ret = build_new_playlist(mock_spotify, "test_user", "r/techno", new_tracks)
    assert isinstance(ret, dict)


@pytest.mark.parametrize("spotify_next_fails", [True, False])
@mock.patch(
    "djtools.spotify.spotify_playlist_builder.filter_tracks",
    return_value=[
        (
            {
                "id": "some_id",
                "name": "Arctic Oscillations",
                "artists": [ 
                    {"name": "Fanu"},
                ],
            },
            "Arctic Oscillations - Fanu" 
        )
    ],
)
@mock.patch("djtools.spotify.spotify_playlist_builder.spotipy.Spotify")
def test_filter_results(mock_spotify, mock_spotify_next, spotify_next_fails):
    results = {
        "tracks": {
            "items": [
                {
                    "track": {
                        "name": "Arctic Oscillations",
                        "artists": [ 
                            {"name": "Fanu"},
                        ],
                    },
                },
                {
                    "track": {
                        "name": "definitely not a matching title",
                        "artists": [ 
                            {"name": "not the right artist"},
                        ],
                    },
                },
            ],
            "next": True,
        },
    }
    threshold = 100
    title = "Arctic Oscillations"
    artist = "Fanu"
    mock_spotify.next.return_value = mock_spotify_next.return_value
    with mock.patch(
        "djtools.spotify.spotify_playlist_checker.spotipy.Spotify.next",
        return_value={
            "tracks": {
                "items": [
                    {
                        "track": {
                            "name": "last track title",
                            "artists": [ 
                                {"name": "final artist name"},
                            ],
                        },
                    },
                ],
                "next": False,
            },
        },
    ) as mock_spotify_next:
        if spotify_next_fails:
            mock_spotify_next.side_effect = Exception()
        ret = filter_results(mock_spotify, results, threshold, title, artist)
    expected = {
        "id": "some_id",
        "name": "Arctic Oscillations",
        "artists": [ 
            {"name": "Fanu"},
        ],
    }
    assert ret == expected


def test_filter_tracks():
    tracks = [
        {
            "name": "Arctic Oscillations",
            "artists": [ 
                {"name": "Fanu"},
            ],
        },
        {
            "name": "definitely not a matching title",
            "artists": [ 
                {"name": "not the right artist"},
            ],
        },
    ]
    threshold = 100
    title = "Arctic Oscillations"
    artist = "Fanu"
    ret = filter_tracks(tracks, threshold, title, artist)
    expected = [
        (
            {
                "name": title,
                "artists": [ 
                    {"name": artist},
                ],
            },
            threshold 
        )
    ]
    assert ret == expected


@pytest.mark.parametrize("match_result", [True, False])
@pytest.mark.parametrize(
    "title",
    [
        ("Arctic Oscillations", "Fanu"),
        ("Fanu", "Arctic Oscillations"),
        (None, None),
        ("something", None),
    ],
)
@mock.patch("djtools.spotify.spotify_playlist_builder.spotipy.Spotify")
@mock.patch(
    "djtools.spotify.spotify_playlist_checker.spotipy.Spotify.search",
    return_value={
        "tracks": {
            "items": [
                {
                    "track": {
                        "name": "Arctic Oscillations",
                        "artists": [ 
                            {"name": "Fanu"},
                        ],
                    },
                },
                {
                    "track": {
                        "name": "definitely not a matching title",
                        "artists": [ 
                            {"name": "not the right artist"},
                        ],
                    },
                },
            ],
            "next": False,
        },
    },
)
def test_fuzzy_match(mock_spotify_search, mock_spotify, title, match_result):
    mock_spotify.search.return_value = mock_spotify_search.return_value
    threshold = 100
    with mock.patch(
        "djtools.spotify.spotify_playlist_builder.parse_title",
        return_value=title,
    ), mock.patch(
        "djtools.spotify.spotify_playlist_builder.filter_results",
        return_value={
            "id": "some_id",
            "name": "Arctic Oscillations",
            "artists": [ 
                {"name": "Fanu"},
            ],
        } if match_result else None,
    ) as mock_filter_results:
        ret = fuzzy_match(mock_spotify, title, threshold)
    if not all(x for x in title):
        assert not ret
    if not match_result:
        assert not ret
    if match_result and all(x for x in title):
        assert isinstance(ret, tuple)
        id_, match = ret
        expected_ret = mock_filter_results.return_value
        assert id_ == expected_ret["id"]
        artists = ", ".join([y["name"] for y in expected_ret["artists"]])
        assert match == f'{expected_ret["name"]} - {artists}'


@mock.patch("djtools.spotify.spotify_playlist_builder.spotipy.Spotify")
@mock.patch(
    "djtools.spotify.spotify_playlist_checker.spotipy.Spotify.search",
    side_effect=Exception()
)
def test_fuzzy_match_handles_spotify_exception(
    mock_spotify_search, mock_spotify, caplog
):
    caplog.set_level("ERROR")
    mock_spotify.search.side_effect = mock_spotify_search.side_effect
    threshold = 100
    title = "Arctic Oscillations"
    artist = "Fanu"
    with mock.patch(
        "djtools.spotify.spotify_playlist_builder.parse_title",
        return_value=(title, artist),
    ):
        ret = fuzzy_match(mock_spotify, title, threshold)
        assert caplog.records[0].message.startswith(
            f'Error searching for "{title} - {artist}"'
        )
        assert not ret


@pytest.mark.asyncio
@pytest.mark.parametrize("subreddit_type", ["hot", "top"])
@pytest.mark.parametrize("num_subs", [5, 0])
@mock.patch("djtools.spotify.spotify_playlist_builder.praw.Reddit.close")
@mock.patch("djtools.spotify.spotify_playlist_builder.process")
@mock.patch("djtools.spotify.spotify_playlist_builder.praw.models.Submission")
@mock.patch("djtools.spotify.spotify_playlist_builder.praw.Reddit")
@mock.patch("djtools.spotify.spotify_playlist_builder.spotipy.Spotify")
async def test_get_subreddit_posts(
    mock_spotify,
    mock_praw,
    mock_praw_submission,
    mock_process,
    mock_praw_close,
    subreddit_type,
    num_subs,
    test_config,
    caplog,
):
    caplog.set_level("INFO")
    subreddit = {
        "name": "techno", "type": subreddit_type, "period": "week", "limit": 50
    }
    praw_cache = {}
    mock_praw_submission.id = "test_id"
    mock_process.return_value = "track - artist"
    with mock.patch(
        "djtools.spotify.spotify_playlist_builder.catch",
    ) as mock_catch, mock.patch(
        "djtools.spotify.spotify_playlist_builder.praw.Reddit.subreddit",
        new=mock.AsyncMock(),
    ):
        mock_catch.return_value=aiter(mock_praw_submission, num_subs)
        await get_subreddit_posts(
            mock_spotify, mock_praw, subreddit, test_config, praw_cache
        )
    assert caplog.records[0].message == (
        f'Filtering {num_subs} "r/techno" {subreddit_type} posts'
    )
    if not num_subs:
        assert caplog.records[1].message == (
            'No new submissions from "r/techno"'        
        )
    else:
        assert caplog.records[1].message == (
            'Searching Spotify for 1 new submission(s) from "r/techno"'
        )
        assert caplog.records[2].message == (
            'Got 1 Spotify track(s) from new "r/techno" posts'
        )


@pytest.mark.asyncio
@mock.patch("djtools.spotify.spotify_playlist_builder.praw.Reddit")
@mock.patch("djtools.spotify.spotify_playlist_builder.spotipy.Spotify")
async def test_get_subreddit_posts_handle_bad_subreddit_method(
    mock_spotify, mock_praw, test_config
):
    subreddit_type = "not-a-method"
    subreddit = {
        "name": "techno", "type": subreddit_type, "period": "week", "limit": 50
    }
    praw_cache = {}
    with mock.patch(
        "djtools.spotify.spotify_playlist_builder.praw.Reddit.subreddit",
        new=mock.AsyncMock(side_effect=lambda *args: None),
    ):
        with pytest.raises(
            AttributeError,
            match=(
                f'Method "{subreddit_type}" does not exist in "Subreddit" '
                "class"
            ),
        ):
            await get_subreddit_posts(
                mock_spotify, mock_praw, subreddit, test_config, praw_cache
            )


@pytest.mark.parametrize(
    "title",
    [
        "Arctic Oscillations - Fanu",
        "Arctic Oscillations - Fanu (this track is cool)",
        "Arctic Oscillations - Fanu [love this track]",
        "Fanu - Arctic Oscillations",
        "A submission title that doesn't include the artist or track info",
    ],
)
def test_parse_title(title):
    split_chars = ["[", "("]
    ret = parse_title(title)
    assert isinstance(ret, tuple)
    if " - " in title:
        assert all(x for x in ret)
        if any(x in title for x in split_chars): 
            assert all(x not in r for x in split_chars for r in ret)
    else:
        assert not any(x for x in ret)


@pytest.mark.parametrize(
    "url",
    [
        "https://open.spotify.com/track/1lps8esDJ9M6rG3HBjhuux",
        "https://some-other-url.com/some_id",
        "",
    ]
)
@pytest.mark.parametrize(
    "title",
    [
        "Arctic Oscillations - Fanu",
        "Fanu - Arctic Oscillations",
        "A submission title that doesn't include the artist or track info",
    ]
)
@mock.patch("djtools.spotify.spotify_playlist_builder.spotipy.Spotify")
@mock.patch(
    "djtools.spotify.spotify_playlist_builder.praw.models.Submission",
    autospec=True
)
def test_process(mock_praw_submission, mock_spotipy, url, title):
    mock_praw_submission.url = url
    mock_praw_submission.title = title 
    with mock.patch(
        "djtools.spotify.spotify_playlist_builder.fuzzy_match",
        return_value=(url, title)
    ):
        ret = process(mock_praw_submission, mock_spotipy, 50)
    assert isinstance(ret, tuple)
    assert ret == (url, title)


@pytest.mark.parametrize(
    "playlist_track_names", [
        ["Arctic Oscillations - Fanu"], ["Not a Match - Some Artist"],
    ],
)
def test_track_name_too_similar(playlist_track_names, caplog):
    caplog.set_level("WARNING")
    track = "Arctic Oscillations - Fanu"
    ret = track_name_too_similar(track, playlist_track_names)
    if any("Not a Match" in x for x in playlist_track_names):
        assert not ret
    else:
        assert ret
        assert caplog.records[0].message == (
            f'Candidate new track "{track}" is too similar to existing '
            f'track "{playlist_track_names[0]}"'
        )


@mock.patch(
    "djtools.spotify.spotify_playlist_builder.async_update_auto_playlists",
    return_value=lambda x: None,
)
def test_update_auto_playlists(
    mock_async_update_auto_playlists, test_config
):
    update_auto_playlists(test_config)


@pytest.mark.parametrize("track_name_too_similar", [True, False])
@mock.patch(
    "djtools.spotify.spotify_playlist_builder.track_name_too_similar",
    return_value=None,
)
@mock.patch(
    "djtools.spotify.spotify_playlist_builder.spotipy.Spotify."
    "playlist_add_items",
    return_value=()
)
@mock.patch(
    "djtools.spotify.spotify_playlist_builder.spotipy.Spotify."
    "playlist_remove_specific_occurrences_of_items",
    return_value=(),
)
@mock.patch(
    "djtools.spotify.spotify_playlist_builder.spotipy.Spotify.track",
    return_value={
        "id": "test_id",
        "name": "track title",
        "artists": [{"name": "artist name"}],
    },
)
@mock.patch(
    "djtools.spotify.spotify_playlist_builder.spotipy.Spotify.next",
    return_value={
        "tracks": {
            "items": [
                {
                    "track": {
                        "id": (
                            "https://open.spotify.com/track/"
                            "1lps8esDJ9M6rG3HBjhuux",
                        ),
                        "name": "last track title",
                        "artists": [ 
                            {"name": "final artist name"},
                        ],
                    },
                },
            ],
            "next": False,
        },
    },
)
@mock.patch(
    "djtools.spotify.spotify_playlist_builder.spotipy.Spotify.playlist",
    return_value={
        "tracks": {
            "items": [
                {
                    "track": {
                        "uri": "test_uri",
                        "id": "test_id",
                        "name": "last track title",
                        "artists": [ 
                            {"name": "final artist name"},
                        ],
                    },
                },
            ],
            "next": True,
        },
    },
)
@mock.patch("djtools.spotify.spotify_playlist_builder.spotipy.Spotify")
def test_update_existing_playlist(
    mock_spotify,
    mock_spotify_playlist,
    mock_spotify_next,
    mock_spotify_track,
    mock_spotify_playlist_remove_specific_occurrences_of_items,
    mock_spotify_playlist_add_items,
    mock_track_name_too_similar,
    track_name_too_similar,
    caplog,
):
    caplog.set_level("WARNING")
    mock_spotify.playlist.return_value = mock_spotify_playlist.return_value
    mock_spotify.next.return_value = mock_spotify_next.return_value
    mock_spotify.track.return_value = mock_spotify_track.return_value
    mock_spotify.playlist_remove_specific_occurrences_of_items.return_value = (
        mock_spotify_playlist_remove_specific_occurrences_of_items.return_value
    )
    mock_spotify.playlist_add_items.return_value = (
        mock_spotify_playlist_add_items.return_value
    )
    mock_track_name_too_similar.return_value = track_name_too_similar
    playlist = ""
    new_tracks = [
        ("test_id", "test track"),
        ("unique_id", "another track"),
        ("https://open.spotify.com/track/1lps8esDJ9M6rG3HBjhuux", "a track"),
    ]
    limit = 1
    verbosity = 1
    ret = update_existing_playlist(
        mock_spotify, playlist, new_tracks, limit, verbosity
    )
    assert isinstance(ret, dict)
    assert caplog.records[0].message == (
        'Candidate new track "test track" is already in the playlist'
    )
