"""Testing for the playlist_builder module."""
from pathlib import Path
from unittest import mock

import pytest

from djtools.spotify.config import SubredditConfig
from djtools.spotify.playlist_builder import (
    async_spotify_playlists,
    spotify_playlist_from_upload,
    spotify_playlists,
)
from djtools.utils.helpers import MockOpen


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "playlist_subreddits", [[], [SubredditConfig(name="jungle").dict()]],
)
@pytest.mark.parametrize("got_playlist_ids", [True, False])
@pytest.mark.parametrize("got_tracks", [True, False])
@mock.patch.object(Path, "exists", mock.Mock(return_value=True))
@mock.patch(
    "djtools.spotify.helpers.update_existing_playlist",
    mock.Mock(
        return_value={
            "name": "test_playlist",
            "external_urls": {"spotify": "https://test-url.com"},
            "id": "test-id",
        },
    ),
)
@mock.patch(
    "djtools.spotify.helpers.build_new_playlist",
    mock.Mock(
        return_value={
            "name": "test_playlist",
            "external_urls": {"spotify": "https://test-url.com"},
            "id": "test-id",
        },
    ),
)
@mock.patch(
    "djtools.spotify.playlist_builder.get_subreddit_posts",
    return_value=[
        [("track-id", "track name")], SubredditConfig(name="jungle").dict()],
)
@mock.patch(
    "djtools.spotify.playlist_builder.get_spotify_client", mock.MagicMock()
)
async def test_async_spotify_playlists(
    mock_get_subreddit_posts,
    got_tracks,
    got_playlist_ids,
    playlist_subreddits,
    config,
):
    """Test for the async_spotify_playlists function."""
    if not got_tracks:
        mock_get_subreddit_posts.return_value[0] = []
    config.SPOTIFY_CLIENT_ID = "test_client_id"
    config.SPOTIFY_CLIENT_SECRET = "test_client_secret"
    config.SPOTIFY_REDIRECT_URI = "test_redirect_uri"
    config.SPOTIFY_PLAYLIST_SUBREDDITS = playlist_subreddits
    with mock.patch(
        "builtins.open",
        MockOpen(
            files=["spotify_playlists.yaml", ".praw.cache"],
            content='{"jungle": "some-id"}' if got_playlist_ids else "{}",
        ).open
    ):
        await async_spotify_playlists(config)


@mock.patch(
    "djtools.spotify.playlist_builder.filter_results",
    mock.Mock(
        return_value=(
            {
                "id": "some_id",
                "name": "some_name",
                "artists": [ 
                    {"name": "some_artist"},
                ],
            },
            100,
        )
    ),
)
@mock.patch(
    "djtools.spotify.playlist_builder.populate_playlist",
    mock.Mock(
        return_value={"some-playlist": "some-id"},
    ),
)
@mock.patch(
    "djtools.spotify.playlist_builder.get_spotify_client", mock.MagicMock()
)
@mock.patch(
    "pyperclip.paste",
    return_value="""aweeeezy/Bass/2022-09-03: 5
                   Brazil - A.M.C.mp3
                   Endless Haze - Koherent.mp3
                   Two Rangers - Two Rangers.mp3
                   Under Pressure - Alix Perez, T-Man.mp3
                   zoom.1 - Relativity Lounge, wicker's portal.mp3
                  aweeeezy/House/2022-09-03: 2
                   Shirt - Cour T..mp3
                   UNKNOWN - 1 - Unknown Artist.mp3""",
)
def test_spotify_playlist_from_upload(config):
    """Test for the spotify_playlist_from_upload function."""
    config.SPOTIFY_CLIENT_ID = "test_client_id"
    config.SPOTIFY_CLIENT_SECRET = "test_client_secret"
    config.SPOTIFY_REDIRECT_URI = "test_redirect_uri"
    config.SPOTIFY_PLAYLIST_FROM_UPLOAD = True
    with mock.patch(
        "builtins.open",
        MockOpen(files=["spotify_playlists.yaml"], content="{}").open
    ):
        spotify_playlist_from_upload(config)


@mock.patch(
    "djtools.spotify.playlist_builder.filter_results",
    mock.Mock(
        return_value=({}, 100),
    ),
)
@mock.patch(
    "djtools.spotify.playlist_builder.get_spotify_client", mock.MagicMock()
)
def test_spotify_playlist_from_upload_handles_non_match(config, caplog):
    """Test for the spotify_playlist_from_upload function."""
    caplog.set_level("WARNING")
    title = "Under Pressure"
    artist = "Alix Perez, T-Man"
    config.SPOTIFY_PLAYLIST_FROM_UPLOAD = True
    with mock.patch(
        "builtins.open",
        MockOpen(files=["spotify_playlists.yaml"], content="{}").open
    ), mock.patch(
        "pyperclip.paste",
        return_value=f"""aweeeezy/Bass/2022-09-03: 5
            {title} - {artist}.mp3""",
    ):
        spotify_playlist_from_upload(config)
    assert caplog.records[0].message == (
        f"Could not find a match for {title} - {artist}"
    )


@mock.patch("djtools.spotify.helpers.get_spotify_client")
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.search",
    side_effect=Exception()
)
def test_spotify_playlist_from_upload_handles_spotify_exception(
    mock_spotify_search, mock_spotify, config, caplog
):
    """Test for the spotify_playlist_from_upload function."""
    caplog.set_level("ERROR")
    mock_spotify.return_value.search.side_effect = (
        mock_spotify_search.side_effect
    )
    title = "Under Pressure"
    artist = "Alix Perez, T-Man"
    config.SPOTIFY_PLAYLIST_FROM_UPLOAD = True
    config.SPOTIFY_CLIENT_ID = "test_client_id"
    config.SPOTIFY_CLIENT_SECRET = "test_client_secret"
    config.SPOTIFY_REDIRECT_URI = "test_redirect_uri"
    with mock.patch(
        "builtins.open",
        MockOpen(files=["spotify_playlists.yaml"], content="{}").open
    ), mock.patch(
        "pyperclip.paste",
        return_value=f"""aweeeezy/Bass/2022-09-03: 5
            {title} - {artist}.mp3"""
    ):
        spotify_playlist_from_upload(config)
    assert caplog.records[0].message.startswith(
        f'Error searching for "{title} - {artist}"'
    )


@mock.patch("pyperclip.paste", return_value="")
def test_spotify_playlist_from_upload_raises_runtimeerror(config):
    """Test for the spotify_playlist_from_upload function."""
    config.SPOTIFY_PLAYLIST_FROM_UPLOAD = True
    with pytest.raises(
        RuntimeError,
        match="Generating a Spotify playlist from an upload requires output "
            "from an upload_music Discord webhook to be copied to the "
            "system's clipboard"
    ):
        spotify_playlist_from_upload(config)


@mock.patch(
    "djtools.spotify.playlist_builder.async_spotify_playlists",
    mock.AsyncMock(return_value=lambda x: None),
)
def test_spotify_playlists(config):
    """Test for the spotify_playlists function."""
    spotify_playlists(config)
