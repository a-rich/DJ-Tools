import asyncio
from unittest import mock

import asyncpraw
import pytest
import spotipy

from djtools.spotify.config import SubredditConfig
from djtools.spotify.helpers import (
    build_new_playlist,
    filter_results,
    filter_tracks,
    fuzzy_match,
    get_playlist_ids,
    get_reddit_client,
    get_spotify_client,
    get_subreddit_posts,
    parse_title,
    populate_playlist,
    process,
    track_name_too_similar,
    update_existing_playlist,
    write_playlist_ids
)
from test_data import MockOpen


pytest_plugins = [
    "test_data",
]


async def aiter(obj, num_subs):
    for i in range(num_subs):
        yield obj
        await asyncio.sleep(0.1)


@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify."
    "playlist_add_items",
    return_value=(),
)
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify."
    "user_playlist_create",
    return_value={"id": "test_id"},
)
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify",
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
    "djtools.spotify.helpers.filter_tracks",
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
@mock.patch("djtools.spotify.helpers.spotipy.Spotify")
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
        "djtools.spotify.helpers.spotipy.Spotify.next",
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
@mock.patch("djtools.spotify.helpers.spotipy.Spotify")
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.search",
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
        "djtools.spotify.helpers.parse_title",
        return_value=title,
    ), mock.patch(
        "djtools.spotify.helpers.filter_results",
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


@mock.patch("djtools.spotify.helpers.get_spotify_client")
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.search",
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
        "djtools.spotify.helpers.parse_title",
        return_value=(title, artist),
    ):
        ret = fuzzy_match(mock_spotify, title, threshold)
        assert caplog.records[0].message.startswith(
            f'Error searching for "{title} - {artist}"'
        )
        assert not ret


@mock.patch(
    "builtins.open",
    MockOpen(
        files=["spotify_playlists.yaml"],
        content="playlist: playlist-id",
    ).open
)
def test_get_playlist_ids():
    playlist_ids = get_playlist_ids()
    assert isinstance(playlist_ids, dict)


@mock.patch("djtools.spotify.helpers.praw.Reddit")
def test_get_reddit_client(test_config):
    test_config.REDDIT_CLIENT_ID = "test_client_id"
    test_config.REDDIT_CLIENT_SECRET = "test_client_secret"
    test_config.REDDIT_USER_AGENT = "test_user_agent"
    get_reddit_client(test_config)


@mock.patch("djtools.spotify.helpers.spotipy.Spotify")
def test_get_spotify_client(test_config):
    test_config.SPOTIFY_CLIENT_ID = "test_client_id"
    test_config.SPOTIFY_CLIENT_SECRET = "test_client_secret"
    test_config.SPOTIFY_REDIRECT_URI = "test_redirect_uri"
    get_spotify_client(test_config)


@pytest.mark.asyncio
@pytest.mark.parametrize("subreddit_type", ["hot", "top"])
@pytest.mark.parametrize("num_subs", [5, 0])
@mock.patch("djtools.spotify.helpers.praw.Reddit.close")
@mock.patch("djtools.spotify.helpers.process")
@mock.patch("djtools.spotify.helpers.praw.models.Submission")
@mock.patch("djtools.spotify.helpers.praw.Reddit")
@mock.patch("djtools.spotify.helpers.get_spotify_client")
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
    subreddit = SubredditConfig(name="techno", type=subreddit_type).dict()
    praw_cache = {}
    mock_praw_submission.id = "test_id"
    mock_process.return_value = "track - artist"
    with mock.patch(
        "djtools.utils.helpers.catch",
    ) as mock_catch, mock.patch(
        "djtools.spotify.helpers.praw.Reddit.subreddit",
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


@pytest.mark.parametrize("playlist_ids", [{}, {"playlist": "id"}])
@pytest.mark.parametrize("tracks", [[], [("id", "title - artist")]])
@mock.patch("djtools.spotify.helpers.spotipy.Spotify.playlist")
@mock.patch("djtools.spotify.helpers.build_new_playlist")
@mock.patch("djtools.spotify.helpers.update_existing_playlist")
@mock.patch("djtools.spotify.helpers.spotipy.Spotify")
def test_populate_playlist(
    mock_spotify,
    mock_update_existing_playlist,
    mock_build_new_playlist,
    mock_spotify_playlist,
    playlist_ids,
    tracks,
    caplog,
):
    ret_val = {
        "name": "playlist",
        "external_urls": {"spotify": "https://test-url.com"},
        "id": "test-id",
    }
    mock_update_existing_playlist.return_value = ret_val
    mock_build_new_playlist.return_value = ret_val
    mock_spotify_playlist.return_value = ret_val
    caplog.set_level("INFO")
    playlist_name = "playlist"
    spotify_username = "test"
    playlist_limit = 50
    ret_playlist_ids = populate_playlist(
        playlist_name=playlist_name,
        playlist_ids=dict(playlist_ids),
        spotify_username=spotify_username,
        spotify=mock_spotify,
        tracks=tracks,
        playlist_limit=playlist_limit,
    )
    if playlist_ids and tracks:
        assert mock_update_existing_playlist.call_count == 1
    elif tracks:
        assert caplog.records.pop(0).message == (
            f"Unable to get ID for {playlist_name}...creating a new playlist"
        )
        assert mock_build_new_playlist.call_count == 1
        assert playlist_name in ret_playlist_ids
    elif playlist_ids:
        assert mock_spotify_playlist.call_count == 1

    if not (playlist_ids or tracks):
        assert (
            mock_update_existing_playlist.call_count == 
            mock_build_new_playlist.call_count == 
            mock_spotify_playlist.call_count == 0
        )
        assert len(caplog.records) == 0
    else:
        assert caplog.records.pop(0).message == (
            f'"{ret_val["name"]}": {ret_val["external_urls"].get("spotify")}'
        )


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
@mock.patch("djtools.spotify.helpers.get_spotify_client")
@mock.patch(
    "djtools.spotify.helpers.praw.models.Submission",
    autospec=True
)
def test_process(mock_praw_submission, mock_spotipy, url, title):
    mock_praw_submission.url = url
    mock_praw_submission.title = title 
    with mock.patch(
        "djtools.spotify.helpers.fuzzy_match",
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


@pytest.mark.parametrize("track_name_too_similar", [True, False])
@mock.patch(
    "djtools.spotify.helpers.track_name_too_similar",
    return_value=None,
)
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify."
    "playlist_add_items",
    return_value=()
)
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify."
    "playlist_remove_specific_occurrences_of_items",
    return_value=(),
)
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.track",
    return_value={
        "id": "test_id",
        "name": "track title",
        "artists": [{"name": "artist name"}],
    },
)
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.next",
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
    "djtools.spotify.helpers.spotipy.Spotify.playlist",
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
@mock.patch("djtools.spotify.helpers.get_spotify_client")
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


@mock.patch(
    "builtins.open", MockOpen(files=["spotify_playlists.yaml"]).open
)
def test_write_playlist_ids():
        write_playlist_ids({})
