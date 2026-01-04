"""Testing for the helpers module.

Note: Core Spotify functionality is tested in the spotify-tools library.
These tests focus on DJ-Tools specific integration and helper functions.
"""

import asyncio
from pathlib import Path
from unittest import mock

import pytest
import yaml

from djtools.spotify.config import SubredditConfig, SubredditType
from djtools.spotify.helpers import (
    _build_new_playlist,
    _catch,
    _parse_title,
    _process,
    _track_name_too_similar,
    filter_results,
    get_playlist_ids,
    get_reddit_client,
    get_spotify_client,
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
    ret = _build_new_playlist(
        mock_client, "test_user", "r/techno", new_tracks
    )
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
        ret_playlist_ids = populate_playlist(
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
