"""Testing for the helpers module.

Note: Core Spotify functionality is tested in the spotify-tools library.
These tests focus on DJ-Tools specific integration and helper functions.
"""

import asyncio
from pathlib import Path
from unittest import mock

import pytest
import yaml

from djtools.spotify.helpers import (
    _build_new_playlist,
    _catch,
    _filter_tracks,
    _fuzzy_match,
    _parse_title,
    _process,
    _track_name_too_similar,
    _update_existing_playlist,
    filter_results,
    get_playlist_ids,
    get_reddit_client,
    get_spotify_client,
    get_subreddit_posts,
    populate_playlist,
    write_playlist_ids,
)

from ..test_utils import mock_exists, MockOpen


async def _aiter(obj, num_subs):
    """Helper function for mocking asyncpraw."""
    for _ in range(num_subs):
        yield obj
        await asyncio.sleep(0.1)


@mock.patch("djtools.spotify.helpers.Client")
def test_build_new_playlist(mock_client):
    """Test for the _build_new_playlist function."""
    mock_client.user_playlist_create.return_value = {"id": "test_id"}
    new_tracks = [("test_id", "track title - artist name")]
    ret = _build_new_playlist(mock_client, "test_user", "r/techno", new_tracks)
    assert isinstance(ret, dict)
    assert ret == {"id": "test_id"}
    mock_client.user_playlist_create.assert_called_once()
    mock_client.playlist_add_items.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("message", ["", "oops"])
async def test_catch(message, caplog):
    """Test for the _catch function."""
    exc = ZeroDivisionError("You can't divide by zero!")

    class Generator:
        """Dummy async generator class."""

        def __init__(self):
            self._iters = 2
            self._i = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._i >= self._iters:
                raise StopAsyncIteration
            self._i += 1
            await asyncio.sleep(0.1)
            if self._i % 2 == 0:
                raise exc
            return self._i

    caplog.set_level("WARNING")
    _ = [x async for x in _catch(Generator(), message=message)]
    assert caplog.records[0].message == (
        f"{message}: {str(exc)}" if message else str(exc)
    )


@mock.patch(
    "builtins.open",
    MockOpen(
        files=["spotify_playlists.yaml"],
        content="playlist: playlist-id",
    ).open,
)
@pytest.mark.parametrize(
    "config_exists, expected",
    [(True, {"playlist": "playlist-id"}), (False, {})],
)
def test_get_playlist_ids(config_exists, expected):
    """Test for the get_playlist_ids function."""
    with mock.patch(
        "djtools.collection.config.Path.exists",
        lambda path: mock_exists(
            [("spotify_playlists.yaml", config_exists)],
            path,
        ),
    ):
        playlist_ids = get_playlist_ids()
    assert isinstance(playlist_ids, dict)
    assert playlist_ids == expected


@mock.patch("djtools.spotify.helpers.praw.Reddit")
def test_get_reddit_client(mock_reddit, config):
    """Test for the get_reddit_client function."""
    config.spotify.reddit_client_id = "test_client_id"
    config.spotify.reddit_client_secret = "test_client_secret"
    config.spotify.reddit_user_agent = "test_user_agent"
    get_reddit_client(config)
    mock_reddit.assert_called_once()


@pytest.mark.parametrize("is_spotify_config", [True, False])
@mock.patch("djtools.spotify.helpers.Client")
def test_get_spotify_client(mock_client, is_spotify_config, config):
    """Test for the get_spotify_client function."""
    if is_spotify_config:
        config = config.spotify

    config.spotify_client_id = "test_client_id"
    config.spotify_client_secret = "test_client_secret"
    config.spotify_redirect_uri = "test_redirect_uri"

    get_spotify_client(config)
    mock_client.assert_called_once()


@pytest.mark.parametrize(
    "title",
    [
        "Arctic Oscillations by Fanu",
        "Arctic Oscillations - Fanu",
        "Arctic Oscillations - Fanu (this track is cool)",
        "Arctic Oscillations - Fanu [love this track]",
        "Fanu - Arctic Oscillations",
        "A submission title that doesn't include the artist or track info",
    ],
)
def test_parse_title(title):
    """Test for the _parse_title function."""
    split_chars = ["[", "("]
    ret = _parse_title(title)
    assert isinstance(ret, list)
    if " - " in title or " by " in title:
        assert all(x for x in ret)
        if any(x in title for x in split_chars):
            assert all(x not in r for x in split_chars for r in ret)
    else:
        assert not any(x for x in ret)


@pytest.mark.parametrize("playlist_ids", [{}, {"playlist": "id"}])
@pytest.mark.parametrize("tracks", [[], [("id", "title - artist")]])
@mock.patch("djtools.spotify.helpers.Client")
def test_populate_playlist(
    mock_client,
    playlist_ids,
    tracks,
    caplog,
):
    """Test for the populate_playlist function."""
    ret_val = {
        "name": "playlist",
        "external_urls": {"spotify": "https://test-url.com"},
        "id": "test-id",
    }
    mock_client.playlist.return_value = ret_val
    mock_client.user_playlist_create.return_value = ret_val
    caplog.set_level("INFO")

    with mock.patch(
        "djtools.spotify.helpers._update_existing_playlist",
        return_value=ret_val,
    ) as mock_update:
        populate_playlist(
            playlist_name="playlist",
            playlist_ids=dict(playlist_ids),
            spotify_username="test",
            spotify=mock_client,
            tracks=tracks,
            playlist_limit=50,
        )

    if playlist_ids and tracks:
        assert mock_update.call_count == 1
    elif tracks:
        assert "Unable to get ID for playlist" in caplog.text
    elif playlist_ids:
        mock_client.playlist.assert_called_once()

    if not (playlist_ids or tracks):
        assert mock_update.call_count == 0


@pytest.mark.parametrize(
    "url",
    [
        "https://open.spotify.com/track/1lps8esDJ9M6rG3HBjhuux",
        "https://some-other-url.com/some_id",
    ],
)
@mock.patch("djtools.spotify.helpers.Client")
@mock.patch("djtools.spotify.helpers.praw.models.Submission")
def test_process(mock_submission, mock_client, url):
    """Test for the _process function."""
    title = "Arctic Oscillations - Fanu"
    mock_submission.url = url
    mock_submission.title = title

    with mock.patch(
        "djtools.spotify.helpers._fuzzy_match", return_value=(url, title)
    ):
        ret = _process(mock_submission, mock_client, 50)

    assert isinstance(ret, tuple)
    assert ret == (url, title)


@pytest.mark.parametrize(
    "playlist_track_names",
    [
        {"Arctic Oscillations - Fanu"},
        {"Not a Match - Some Artist"},
    ],
)
def test_track_name_too_similar(playlist_track_names, caplog):
    """Test for the _track_name_too_similar function."""
    caplog.set_level("WARNING")
    track = "Arctic Oscillations - Fanu"
    ret = _track_name_too_similar(track, playlist_track_names)
    if any("Not a Match" in x for x in playlist_track_names):
        assert not ret
    else:
        assert ret
        assert "too similar" in caplog.text


def test_write_playlist_ids():
    """Test for the write_playlist_ids function."""
    ids_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "djtools"
        / "configs"
        / "spotify_playlists.yaml"
    )

    # Write a playlist to the config
    test_data = {"playlist": "playlist-id", "another": "another-id"}
    write_playlist_ids(test_data)

    with open(ids_path, mode="r", encoding="utf-8") as _file:
        data = yaml.load(_file, Loader=yaml.FullLoader)

    assert data == test_data

    # Clean up
    ids_path.unlink()


@mock.patch("djtools.spotify.helpers.Client")
def test_filter_results_with_matches(mock_client):
    """Test filter_results returns best match."""
    results = {
        "tracks": {
            "items": [
                {
                    "id": "track1",
                    "name": "Test Song",
                    "artists": [{"name": "Test Artist"}],
                    "uri": "spotify:track:track1",
                }
            ],
            "next": None,
        }
    }

    track, score = filter_results(
        mock_client, results, 70.0, "Test Song", "Test Artist"
    )

    assert track.get("id") == "track1"
    assert score > 0


@mock.patch("djtools.spotify.helpers.Client")
def test_filter_results_no_matches(mock_client):
    """Test filter_results returns empty when no matches."""
    results = {
        "tracks": {
            "items": [
                {
                    "id": "track1",
                    "name": "Completely Different",
                    "artists": [{"name": "Unknown"}],
                    "uri": "spotify:track:track1",
                }
            ],
            "next": None,
        }
    }

    track, score = filter_results(
        mock_client, results, 90.0, "Test Song", "Test Artist"
    )

    assert track == {}
    assert score == 0.0


@mock.patch("djtools.spotify.helpers.Client")
def test_filter_results_with_pagination(mock_client):
    """Test filter_results handles pagination."""
    results = {
        "tracks": {
            "items": [
                {
                    "id": "track1",
                    "name": "First Track",
                    "artists": [{"name": "Artist"}],
                    "uri": "spotify:track:track1",
                }
            ],
            "next": "https://api.spotify.com/next",
        }
    }
    mock_client.next.return_value = {
        "tracks": {
            "items": [
                {
                    "id": "track2",
                    "name": "Test Song",
                    "artists": [{"name": "Test Artist"}],
                    "uri": "spotify:track:track2",
                }
            ],
            "next": None,
        }
    }

    track, score = filter_results(
        mock_client, results, 70.0, "Test Song", "Test Artist"
    )

    assert track.get("id") == "track2"
    assert score > 0
    mock_client.next.assert_called()


@mock.patch("djtools.spotify.helpers.Client")
def test_filter_results_pagination_exception(mock_client, caplog):
    """Test filter_results handles pagination errors."""
    caplog.set_level("WARNING")
    results = {
        "tracks": {
            "items": [
                {
                    "id": "track1",
                    "name": "Test Song",
                    "artists": [{"name": "Test Artist"}],
                    "uri": "spotify:track:track1",
                }
            ],
            "next": "https://api.spotify.com/next",
        }
    }
    mock_client.next.side_effect = Exception("API Error")

    track, _score = filter_results(
        mock_client, results, 70.0, "Test Song", "Test Artist"
    )

    assert track.get("id") == "track1"
    assert "Failed to get next tracks" in caplog.text


@mock.patch("djtools.spotify.helpers.Client")
def test_filter_results_pagination_empty_response(mock_client):
    """Test filter_results handles empty pagination response."""
    results = {
        "tracks": {
            "items": [
                {
                    "id": "track1",
                    "name": "Test Song",
                    "artists": [{"name": "Test Artist"}],
                    "uri": "spotify:track:track1",
                }
            ],
            "next": "https://api.spotify.com/next",
        }
    }
    mock_client.next.return_value = None

    track, _ = filter_results(
        mock_client, results, 70.0, "Test Song", "Test Artist"
    )

    assert track.get("id") == "track1"


@mock.patch("djtools.spotify.helpers.Client")
def test_filter_results_pagination_items_key(mock_client):
    """Test filter_results handles 'items' key in pagination response."""
    results = {
        "tracks": {
            "items": [
                {
                    "id": "track1",
                    "name": "First",
                    "artists": [{"name": "Artist"}],
                    "uri": "spotify:track:track1",
                }
            ],
            "next": "https://api.spotify.com/next",
        }
    }
    # Simulating response where items is at top level instead of tracks.items
    mock_client.next.return_value = {
        "items": [
            {
                "id": "track2",
                "name": "Test Song",
                "artists": [{"name": "Test Artist"}],
                "uri": "spotify:track:track2",
            }
        ],
        "next": None,
    }

    _, score = filter_results(
        mock_client, results, 70.0, "Test Song", "Test Artist"
    )

    assert score > 0


def test_filter_tracks():
    """Test _filter_tracks function."""
    tracks = [
        {
            "id": "track1",
            "name": "Test Song",
            "artists": [{"name": "Test Artist"}],
            "uri": "spotify:track:track1",
        },
        {
            "id": "track2",
            "name": "Another Track",
            "artists": [{"name": "Other Artist"}],
            "uri": "spotify:track:track2",
        },
    ]

    results = _filter_tracks(tracks, 70.0, "Test Song", "Test Artist")
    assert len(results) == 1
    assert results[0][0]["id"] == "track1"
    assert results[0][1] > 0


def test_filter_tracks_no_matches():
    """Test _filter_tracks returns empty when no matches."""
    tracks = [
        {
            "id": "track1",
            "name": "Completely Different",
            "artists": [{"name": "Unknown"}],
            "uri": "spotify:track:track1",
        }
    ]

    results = _filter_tracks(tracks, 90.0, "Test Song", "Test Artist")
    assert results == []


@mock.patch("djtools.spotify.helpers.search_track_fuzzy")
@mock.patch("djtools.spotify.helpers.Client")
def test_fuzzy_match_success(mock_client, mock_search):
    """Test _fuzzy_match returns track when found."""
    mock_track = mock.MagicMock()
    mock_track.id = "track123"
    mock_track.name = "Test Song"
    mock_artist = mock.MagicMock()
    mock_artist.name = "Test Artist"
    mock_track.artists = [mock_artist]

    mock_result = mock.MagicMock()
    mock_result.track = mock_track
    mock_search.return_value = mock_result

    result = _fuzzy_match(mock_client, "Test Song - Test Artist", 70.0)

    assert result is not None
    assert result[0] == "track123"
    assert "Test Song" in result[1]


@mock.patch("djtools.spotify.helpers.search_track_fuzzy")
@mock.patch("djtools.spotify.helpers.Client")
def test_fuzzy_match_no_match(mock_client, mock_search):
    """Test _fuzzy_match returns None when no match found."""
    mock_search.return_value = None

    result = _fuzzy_match(mock_client, "Test Song - Test Artist", 70.0)

    assert result is None


@mock.patch("djtools.spotify.helpers.Client")
def test_fuzzy_match_unparseable_title(mock_client):
    """Test _fuzzy_match returns None for unparseable titles."""
    result = _fuzzy_match(mock_client, "No delimiter here", 70.0)
    assert result is None


@mock.patch("djtools.spotify.helpers.search_track_fuzzy")
@mock.patch("djtools.spotify.helpers.Client")
def test_fuzzy_match_exception(mock_client, mock_search, caplog):
    """Test _fuzzy_match handles exceptions gracefully."""
    caplog.set_level("ERROR")
    mock_search.side_effect = Exception("API Error")

    result = _fuzzy_match(mock_client, "Test Song - Test Artist", 70.0)

    assert result is None
    assert "Error searching" in caplog.text


@mock.patch("djtools.spotify.helpers.Client")
def test_update_existing_playlist_add_tracks(mock_client, caplog):
    """Test _update_existing_playlist adds new tracks."""
    caplog.set_level("INFO")
    playlist_data = {
        "id": "playlist123",
        "name": "Test Playlist",
        "tracks": {
            "items": [
                {
                    "track": {
                        "id": "existing1",
                        "name": "Existing Track",
                        "artists": [{"name": "Artist"}],
                        "uri": "spotify:track:existing1",
                    }
                }
            ],
            "next": None,
        },
    }
    mock_client.playlist.return_value = playlist_data

    new_tracks = [("new_track_id", "New Track - New Artist")]

    result = _update_existing_playlist(
        mock_client, "playlist123", new_tracks, 50, 0
    )

    assert result["id"] == "playlist123"
    mock_client.playlist_add_items.assert_called_once()
    assert "1 new tracks added" in caplog.text


@mock.patch("djtools.spotify.helpers.Client")
def test_update_existing_playlist_duplicate_id(mock_client, caplog):
    """Test _update_existing_playlist skips duplicate track IDs."""
    caplog.set_level("WARNING")
    playlist_data = {
        "id": "playlist123",
        "name": "Test Playlist",
        "tracks": {
            "items": [
                {
                    "track": {
                        "id": "existing1",
                        "name": "Existing Track",
                        "artists": [{"name": "Artist"}],
                        "uri": "spotify:track:existing1",
                    }
                }
            ],
            "next": None,
        },
    }
    mock_client.playlist.return_value = playlist_data

    new_tracks = [("existing1", "Existing Track - Artist")]

    _update_existing_playlist(mock_client, "playlist123", new_tracks, 50, 0)

    mock_client.playlist_add_items.assert_not_called()
    assert "already in the playlist" in caplog.text


@mock.patch("djtools.spotify.helpers.Client")
def test_update_existing_playlist_resolves_url(mock_client, caplog):
    """Test _update_existing_playlist resolves Spotify URLs to track IDs."""
    caplog.set_level("INFO")
    playlist_data = {
        "id": "playlist123",
        "name": "Test Playlist",
        "tracks": {
            "items": [],
            "next": None,
        },
    }
    mock_client.playlist.return_value = playlist_data
    mock_client.track.return_value = {
        "id": "resolved_id",
        "name": "Resolved Track",
        "artists": [{"name": "Artist"}],
    }

    new_tracks = [
        (
            "https://open.spotify.com/track/abc123",
            "Some Track - Some Artist",
        )
    ]

    _update_existing_playlist(mock_client, "playlist123", new_tracks, 50, 0)

    mock_client.track.assert_called_once()
    mock_client.playlist_add_items.assert_called_once()


@mock.patch("djtools.spotify.helpers.Client")
def test_update_existing_playlist_removes_old_tracks(mock_client, caplog):
    """Test _update_existing_playlist removes old tracks when limit exceeded."""
    caplog.set_level("INFO")
    playlist_data = {
        "id": "playlist123",
        "name": "Test Playlist",
        "tracks": {
            "items": [
                {
                    "track": {
                        "id": "old1",
                        "name": "Old Track",
                        "artists": [{"name": "Artist"}],
                        "uri": "spotify:track:old1",
                    }
                }
            ],
            "next": None,
        },
    }
    mock_client.playlist.return_value = playlist_data

    new_tracks = [("new1", "New Track - Artist")]

    _update_existing_playlist(mock_client, "playlist123", new_tracks, 1, 0)

    mock_client.playlist_remove_specific_occurrences_of_items.assert_called()
    mock_client.playlist_add_items.assert_called_once()
    assert "1 old tracks removed" in caplog.text


@mock.patch("djtools.spotify.helpers.Client")
def test_update_existing_playlist_verbose_logging(mock_client, caplog):
    """Test _update_existing_playlist logs track details when verbose."""
    caplog.set_level("INFO")
    playlist_data = {
        "id": "playlist123",
        "name": "Test Playlist",
        "tracks": {
            "items": [],
            "next": None,
        },
    }
    mock_client.playlist.return_value = playlist_data

    new_tracks = [("new1", "New Track - Artist")]

    _update_existing_playlist(mock_client, "playlist123", new_tracks, 50, 1)

    assert "New Track - Artist" in caplog.text


@mock.patch("djtools.spotify.helpers.Client")
def test_update_existing_playlist_no_changes(mock_client, caplog):
    """Test _update_existing_playlist logs when no changes made."""
    caplog.set_level("INFO")
    playlist_data = {
        "id": "playlist123",
        "name": "Test Playlist",
        "tracks": {
            "items": [
                {
                    "track": {
                        "id": "existing1",
                        "name": "Existing Track",
                        "artists": [{"name": "Artist"}],
                        "uri": "spotify:track:existing1",
                    }
                }
            ],
            "next": None,
        },
    }
    mock_client.playlist.return_value = playlist_data

    new_tracks = [("existing1", "Existing Track - Artist")]

    _update_existing_playlist(mock_client, "playlist123", new_tracks, 50, 0)

    assert "No tracks added or removed" in caplog.text


@mock.patch("djtools.spotify.helpers.Client")
def test_update_existing_playlist_pagination(mock_client):
    """Test _update_existing_playlist handles pagination."""
    page1 = {
        "id": "playlist123",
        "name": "Test Playlist",
        "tracks": {
            "items": [
                {
                    "track": {
                        "id": "track1",
                        "name": "Track 1",
                        "artists": [{"name": "Artist"}],
                        "uri": "spotify:track:track1",
                    }
                }
            ],
            "next": "https://api.spotify.com/next",
        },
    }
    page2 = {
        "tracks": {
            "items": [
                {
                    "track": {
                        "id": "track2",
                        "name": "Track 2",
                        "artists": [{"name": "Artist"}],
                        "uri": "spotify:track:track2",
                    }
                }
            ],
            "next": None,
        }
    }
    mock_client.playlist.return_value = page1
    mock_client.next.return_value = page2

    new_tracks = [("new_track", "New Track - Artist")]

    _update_existing_playlist(mock_client, "playlist123", new_tracks, 50, 0)

    mock_client.next.assert_called()
    mock_client.playlist_add_items.assert_called_once()


@mock.patch("djtools.spotify.helpers.Client")
def test_update_existing_playlist_pagination_items_key(mock_client):
    """Test _update_existing_playlist handles pagination with items key."""
    page1 = {
        "id": "playlist123",
        "name": "Test Playlist",
        "tracks": {
            "items": [
                {
                    "track": {
                        "id": "track1",
                        "name": "Track 1",
                        "artists": [{"name": "Artist"}],
                        "uri": "spotify:track:track1",
                    }
                }
            ],
            "next": "https://api.spotify.com/next",
        },
    }
    # Response with items at top level instead of tracks.items
    page2 = {
        "items": [
            {
                "track": {
                    "id": "track2",
                    "name": "Track 2",
                    "artists": [{"name": "Artist"}],
                    "uri": "spotify:track:track2",
                }
            }
        ],
        "next": None,
    }
    mock_client.playlist.return_value = page1
    mock_client.next.return_value = page2

    new_tracks = [("new_track", "New Track - Artist")]

    _update_existing_playlist(mock_client, "playlist123", new_tracks, 50, 0)

    mock_client.next.assert_called()


@mock.patch("djtools.spotify.helpers.Client")
def test_update_existing_playlist_pagination_error(mock_client, caplog):
    """Test _update_existing_playlist handles pagination errors."""
    caplog.set_level("ERROR")
    page1 = {
        "id": "playlist123",
        "name": "Test Playlist",
        "tracks": {
            "items": [],
            "next": "https://api.spotify.com/next",
        },
    }
    mock_client.playlist.return_value = page1
    mock_client.next.side_effect = Exception("API Error")

    new_tracks = [("new_track", "New Track - Artist")]

    _update_existing_playlist(mock_client, "playlist123", new_tracks, 50, 0)

    assert "Failed to get tracks" in caplog.text


class MockTqdm:
    """Mock tqdm that works both as iterator and context manager."""

    def __init__(
        self, iterable=None, **kwargs
    ):  # pylint: disable=unused-argument
        self.iterable = iterable

    def __iter__(self):
        return iter(self.iterable or [])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def update(self, n=1):
        """Mock update method."""


@pytest.mark.asyncio
@mock.patch("tqdm.tqdm", MockTqdm)
@mock.patch("djtools.spotify.helpers.Client")
async def test_get_subreddit_posts(mock_client, config):
    """Test get_subreddit_posts function."""
    config.spotify.spotify_playlist_post_limit = 10
    config.spotify.spotify_playlist_fuzz_ratio = 70

    mock_reddit = mock.AsyncMock()
    mock_subreddit = mock.AsyncMock()
    mock_reddit.subreddit.return_value = mock_subreddit

    # Create mock submissions
    mock_submission = mock.MagicMock()
    mock_submission.id = "sub123"
    mock_submission.url = "https://open.spotify.com/track/abc123"
    mock_submission.title = "Test Track - Test Artist"

    mock_subreddit.hot = mock.MagicMock(
        return_value=_aiter(mock_submission, 1)
    )

    from djtools.spotify.config import SubredditConfig
    from djtools.spotify.enums import SubredditType

    subreddit_config = SubredditConfig(name="techno", type=SubredditType.HOT)

    tracks, sub = await get_subreddit_posts(
        mock_client, mock_reddit, subreddit_config, config, {}
    )

    assert sub == subreddit_config
    assert len(tracks) == 1


@pytest.mark.asyncio
@mock.patch("tqdm.tqdm", MockTqdm)
@mock.patch("djtools.spotify.helpers.Client")
async def test_get_subreddit_posts_with_cache(mock_client, config, caplog):
    """Test get_subreddit_posts skips cached submissions."""
    caplog.set_level("INFO")
    config.spotify.spotify_playlist_post_limit = 10
    config.spotify.spotify_playlist_fuzz_ratio = 70

    mock_reddit = mock.AsyncMock()
    mock_subreddit = mock.AsyncMock()
    mock_reddit.subreddit.return_value = mock_subreddit

    mock_submission = mock.MagicMock()
    mock_submission.id = "cached_sub"
    mock_submission.url = "https://open.spotify.com/track/abc123"
    mock_submission.title = "Test Track"

    mock_subreddit.hot = mock.MagicMock(
        return_value=_aiter(mock_submission, 1)
    )

    from djtools.spotify.config import SubredditConfig
    from djtools.spotify.enums import SubredditType

    subreddit_config = SubredditConfig(name="techno", type=SubredditType.HOT)
    praw_cache = {"cached_sub": True}

    tracks, _ = await get_subreddit_posts(
        mock_client, mock_reddit, subreddit_config, config, praw_cache
    )

    assert len(tracks) == 0
    assert "No new submissions" in caplog.text


@pytest.mark.asyncio
@mock.patch("tqdm.tqdm", MockTqdm)
@mock.patch("djtools.spotify.helpers.Client")
async def test_get_subreddit_posts_top_type(mock_client, config):
    """Test get_subreddit_posts with TOP subreddit type."""
    config.spotify.spotify_playlist_post_limit = 10
    config.spotify.spotify_playlist_fuzz_ratio = 70

    mock_reddit = mock.AsyncMock()
    mock_subreddit = mock.AsyncMock()
    mock_reddit.subreddit.return_value = mock_subreddit

    mock_submission = mock.MagicMock()
    mock_submission.id = "sub123"
    mock_submission.url = "https://open.spotify.com/track/abc123"
    mock_submission.title = "Test Track"

    mock_subreddit.top = mock.MagicMock(
        return_value=_aiter(mock_submission, 1)
    )

    from djtools.spotify.config import SubredditConfig
    from djtools.spotify.enums import SubredditPeriod, SubredditType

    subreddit_config = SubredditConfig(
        name="techno",
        type=SubredditType.TOP,
        period=SubredditPeriod.WEEK,
    )

    await get_subreddit_posts(
        mock_client, mock_reddit, subreddit_config, config, {}
    )

    # Verify top was called with time_filter
    mock_subreddit.top.assert_called_once()
