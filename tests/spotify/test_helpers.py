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
    _catch,
    _log_update_result,
    _parse_title,
    _process,
    _resolve_tracks,
    filter_results,
    get_playlist_ids,
    get_reddit_client,
    get_spotify_client,
    get_subreddit_posts,
    populate_playlist,
    write_playlist_ids,
)

from ..test_utils import MockOpen, mock_exists


async def _aiter(obj, num_subs):
    """Helper function for mocking asyncpraw."""
    for _ in range(num_subs):
        yield obj
        await asyncio.sleep(0.1)


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
        f"{message}: {exc!s}" if message else str(exc)
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
@mock.patch("djtools.spotify.helpers.update_playlist")
@mock.patch("djtools.spotify.helpers.create_playlist")
@mock.patch("djtools.spotify.helpers.get_playlist")
@mock.patch("djtools.spotify.helpers.Client")
def test_populate_playlist(
    mock_client,
    mock_get_playlist,
    mock_create_playlist,
    mock_update_playlist,
    playlist_ids,
    tracks,
    caplog,
):
    """Test for the populate_playlist function."""
    # Mock playlist response
    mock_playlist = mock.MagicMock()
    mock_playlist.id = "test-id"
    mock_playlist.name = "playlist"
    mock_playlist.external_urls = mock.MagicMock()
    mock_playlist.external_urls.spotify = "https://test-url.com"

    mock_get_playlist.return_value = mock_playlist
    mock_create_playlist.return_value = mock_playlist

    # Mock update result
    mock_result = mock.MagicMock()
    mock_result.tracks_added = []
    mock_result.tracks_removed = []
    mock_result.skipped_existing = []
    mock_result.skipped_duplicates = []
    mock_update_playlist.return_value = mock_result

    caplog.set_level("INFO")

    result = populate_playlist(
        playlist_name="playlist",
        playlist_ids=dict(playlist_ids),
        spotify_username="test",
        spotify=mock_client,
        tracks=tracks,
        playlist_limit=50,
    )

    if playlist_ids and tracks:
        mock_update_playlist.assert_called_once()
    elif tracks:
        assert "Unable to get ID for playlist" in caplog.text
        mock_create_playlist.assert_called_once()
    elif playlist_ids:
        mock_get_playlist.assert_called()

    assert isinstance(result, dict)


@pytest.mark.parametrize(
    "url",
    [
        "https://open.spotify.com/track/1lps8esDJ9M6rG3HBjhuux",
        "https://some-other-url.com/some_id",
    ],
)
@mock.patch("djtools.spotify.helpers.search_track_fuzzy")
@mock.patch("djtools.spotify.helpers.Client")
@mock.patch("djtools.spotify.helpers.praw.models.Submission")
def test_process(mock_submission, mock_client, mock_search, url):
    """Test for the _process function."""
    title = "Arctic Oscillations - Fanu"
    mock_submission.url = url
    mock_submission.title = title

    # Mock search result
    mock_track = mock.MagicMock()
    mock_track.id = "track123"
    mock_track.name = "Arctic Oscillations"
    mock_artist = mock.MagicMock()
    mock_artist.name = "Fanu"
    mock_track.artists = [mock_artist]

    mock_result = mock.MagicMock()
    mock_result.track = mock_track
    mock_search.return_value = mock_result

    ret = _process(mock_submission, mock_client, 50)

    assert isinstance(ret, tuple)
    if "spotify.com/track/" in url:
        assert ret == (url, title)
    else:
        assert ret[0] == "track123"


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


@mock.patch("djtools.spotify.helpers.search_track_fuzzy")
@mock.patch("djtools.spotify.helpers.Client")
def test_filter_results_with_matches(mock_client, mock_search):
    """Test filter_results returns best match."""
    mock_track = mock.MagicMock()
    mock_track.model_dump.return_value = {
        "id": "track1",
        "name": "Test Song",
        "artists": [{"name": "Test Artist"}],
    }

    mock_result = mock.MagicMock()
    mock_result.track = mock_track
    mock_result.score = 180.0
    mock_search.return_value = mock_result

    results = {"tracks": {"items": []}}  # unused but kept for API compat

    track, score = filter_results(
        mock_client, results, 70.0, "Test Song", "Test Artist"
    )

    assert track.get("id") == "track1"
    assert score == 180.0  # noqa: PLR2004


@mock.patch("djtools.spotify.helpers.search_track_fuzzy")
@mock.patch("djtools.spotify.helpers.Client")
def test_filter_results_no_matches(mock_client, mock_search):
    """Test filter_results returns empty when no matches."""
    mock_search.return_value = None

    results = {"tracks": {"items": []}}

    track, score = filter_results(
        mock_client, results, 90.0, "Test Song", "Test Artist"
    )

    assert track == {}
    assert score == 0.0


def test_log_update_result_added_tracks(caplog):
    """Test _log_update_result logs added tracks."""
    caplog.set_level("INFO")

    mock_track = mock.MagicMock()
    mock_track.display_name = "New Track - Artist"

    result = mock.MagicMock()
    result.tracks_added = [mock_track]
    result.tracks_removed = []
    result.skipped_existing = []
    result.skipped_duplicates = []

    _log_update_result(result, 0)

    assert "1 new tracks added" in caplog.text


def test_log_update_result_removed_tracks(caplog):
    """Test _log_update_result logs removed tracks."""
    caplog.set_level("INFO")

    mock_track = mock.MagicMock()
    mock_track.display_name = "Old Track - Artist"

    result = mock.MagicMock()
    result.tracks_added = []
    result.tracks_removed = [mock_track]
    result.skipped_existing = []
    result.skipped_duplicates = []

    _log_update_result(result, 0)

    assert "1 old tracks removed" in caplog.text


def test_log_update_result_skipped_existing(caplog):
    """Test _log_update_result logs skipped existing tracks."""
    caplog.set_level("WARNING")

    mock_track = mock.MagicMock()
    mock_track.display_name = "Existing Track - Artist"

    result = mock.MagicMock()
    result.tracks_added = []
    result.tracks_removed = []
    result.skipped_existing = [mock_track]
    result.skipped_duplicates = []

    _log_update_result(result, 0)

    assert "already in the playlist" in caplog.text


def test_log_update_result_skipped_duplicates(caplog):
    """Test _log_update_result logs skipped duplicate tracks."""
    caplog.set_level("WARNING")

    mock_track = mock.MagicMock()
    mock_track.display_name = "Similar Track - Artist"

    result = mock.MagicMock()
    result.tracks_added = []
    result.tracks_removed = []
    result.skipped_existing = []
    result.skipped_duplicates = [mock_track]

    _log_update_result(result, 0)

    assert "too similar to existing" in caplog.text


def test_log_update_result_no_changes(caplog):
    """Test _log_update_result logs when no changes."""
    caplog.set_level("INFO")

    result = mock.MagicMock()
    result.tracks_added = []
    result.tracks_removed = []
    result.skipped_existing = []
    result.skipped_duplicates = []

    _log_update_result(result, 0)

    assert "No tracks added or removed" in caplog.text


@mock.patch("djtools.spotify.helpers.resolve_track_from_url")
@mock.patch("djtools.spotify.helpers.Client")
def test_resolve_tracks_with_urls(mock_client, mock_resolve):
    """Test _resolve_tracks resolves Spotify URLs."""
    mock_pt = mock.MagicMock()
    mock_pt.id = "resolved_id"
    mock_resolve.return_value = mock_pt

    tracks = [
        ("https://open.spotify.com/track/abc123", "Track - Artist"),
    ]

    result = _resolve_tracks(mock_client, tracks)

    assert len(result) == 1
    mock_resolve.assert_called_once()


@mock.patch("djtools.spotify.helpers.Client")
def test_resolve_tracks_with_ids(mock_client):
    """Test _resolve_tracks creates PlaylistTrack from IDs."""
    tracks = [
        ("track_id_123", "Track Name - Artist Name"),
    ]

    result = _resolve_tracks(mock_client, tracks)

    assert len(result) == 1
    assert result[0].id == "track_id_123"
    assert result[0].name == "Track Name"
    assert result[0].artists == "Artist Name"


@mock.patch("djtools.spotify.helpers.search_track_fuzzy")
@mock.patch("djtools.spotify.helpers.Client")
@mock.patch("djtools.spotify.helpers.praw.models.Submission")
def test_process_unparseable_title(mock_submission, mock_client, mock_search):
    """Test _process returns None for unparseable titles."""
    mock_submission.url = "https://some-url.com"
    mock_submission.title = "No delimiter here"

    ret = _process(mock_submission, mock_client, 50)

    assert ret is None
    mock_search.assert_not_called()


@mock.patch("djtools.spotify.helpers.search_track_fuzzy")
@mock.patch("djtools.spotify.helpers.Client")
@mock.patch("djtools.spotify.helpers.praw.models.Submission")
def test_process_search_exception(
    mock_submission, mock_client, mock_search, caplog
):
    """Test _process handles search exceptions gracefully."""
    caplog.set_level("ERROR")
    mock_submission.url = "https://some-url.com"
    mock_submission.title = "Track Name - Artist"
    mock_search.side_effect = Exception("API Error")

    ret = _process(mock_submission, mock_client, 50)

    assert ret is None
    assert "Error searching" in caplog.text


@mock.patch("djtools.spotify.helpers.search_track_fuzzy")
@mock.patch("djtools.spotify.helpers.Client")
@mock.patch("djtools.spotify.helpers.praw.models.Submission")
def test_process_no_match(mock_submission, mock_client, mock_search):
    """Test _process returns None when no match found."""
    mock_submission.url = "https://some-url.com"
    mock_submission.title = "Track Name - Artist"
    mock_search.return_value = None

    ret = _process(mock_submission, mock_client, 50)

    assert ret is None


class MockTqdm:
    """Mock tqdm that works both as iterator and context manager."""

    def __init__(self, iterable=None, **kwargs):  # pylint: disable=unused-argument
        self.iterable = iterable

    def __iter__(self):
        return iter(self.iterable or [])

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def update(self, n=1):  # pylint: disable=unused-argument
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
