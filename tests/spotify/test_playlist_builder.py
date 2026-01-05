"""Testing for the playlist_builder module.

Note: Core Spotify functionality is tested in the spotify-tools library.
These tests focus on DJ-Tools specific playlist building logic.
"""

from pathlib import Path
from unittest import mock

import pytest

from djtools.spotify.config import SubredditConfig
from djtools.spotify.playlist_builder import (
    async_spotify_playlists,
    spotify_playlist_from_upload,
    spotify_playlists,
)

from ..test_utils import MockOpen


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "playlist_subreddits",
    [[], [SubredditConfig(name="jungle")]],
)
@pytest.mark.parametrize("got_playlist_ids", [True, False])
@pytest.mark.parametrize("got_tracks", [True, False])
@mock.patch.object(Path, "exists", mock.Mock(return_value=True))
@mock.patch(
    "djtools.spotify.playlist_builder.get_subreddit_posts",
    new_callable=mock.AsyncMock,
    return_value=[
        [("track-id", "track name")],
        SubredditConfig(name="jungle"),
    ],
)
@mock.patch("djtools.spotify.playlist_builder.get_spotify_client")
@mock.patch("djtools.spotify.playlist_builder.get_reddit_client")
async def test_async_spotify_playlists(
    mock_reddit_client,
    _mock_spotify_client,
    mock_get_subreddit_posts,
    got_tracks,
    got_playlist_ids,
    playlist_subreddits,
    config,
):
    """Test for the async_spotify_playlists function."""
    if not got_tracks:
        mock_get_subreddit_posts.return_value[0] = []

    config.spotify.spotify_client_id = "test_client_id"
    config.spotify.spotify_client_secret = "test_client_secret"
    config.spotify.spotify_redirect_uri = "test_redirect_uri"
    config.spotify.spotify_playlist_subreddits = playlist_subreddits

    mock_reddit_client.return_value.close = mock.AsyncMock()

    with (
        mock.patch(
            "builtins.open",
            MockOpen(
                files=["spotify_playlists.yaml", ".praw.cache"],
                content='{"jungle": "some-id"}' if got_playlist_ids else "{}",
            ).open,
        ),
        mock.patch(
            "djtools.spotify.playlist_builder.populate_playlist",
            return_value={"jungle": "some-id"},
        ),
    ):
        await async_spotify_playlists(config)


@mock.patch("djtools.spotify.playlist_builder.filter_results")
@mock.patch("djtools.spotify.playlist_builder.populate_playlist")
@mock.patch("djtools.spotify.playlist_builder.get_spotify_client")
@mock.patch(
    "pyperclip.paste",
    return_value="""aweeeezy/Bass/2022-09-03: 5
 Brazil - A.M.C.mp3
 Endless Haze - Koherent.mp3
 Two Rangers - Two Rangers.mp3
 Under Pressure - Alix Perez, T-Man.mp3
 zoom.1 - Relativity Lounge, wicker's portal.mp3
aweeeezy/House/2022-09-03: 2
 Shirt - Cour T..mp3""",
)
def test_spotify_playlist_from_upload(
    _mock_paste,
    _mock_spotify_client,
    mock_populate,
    mock_filter,
    config,
    caplog,
):
    """Test for the spotify_playlist_from_upload function."""
    caplog.set_level("INFO")

    mock_filter.return_value = (
        {
            "id": "some_id",
            "name": "some_name",
            "artists": [{"name": "some_artist"}],
        },
        100,
    )
    mock_populate.return_value = {"some-playlist": "some-id"}

    config.spotify.spotify_client_id = "test_client_id"
    config.spotify.spotify_client_secret = "test_client_secret"
    config.spotify.spotify_redirect_uri = "test_redirect_uri"
    config.spotify.spotify_playlist_from_upload = True

    with mock.patch(
        "builtins.open",
        MockOpen(files=["spotify_playlists.yaml"], content="{}").open,
    ):
        spotify_playlist_from_upload(config)

    for rec in caplog.records:
        assert rec.message.startswith("Matched")


@mock.patch("djtools.spotify.playlist_builder.get_spotify_client")
@mock.patch(
    "pyperclip.paste",
    return_value="""aweeeezy/House/2022-09-03: 2
 UNKNOWN - 1 - Unknown Artist.mp3""",
)
def test_spotify_playlist_from_upload_handles_file_with_multiple_dashes(
    _mock_paste,
    _mock_spotify_client,
    config,
    caplog,
):
    """Test for the spotify_playlist_from_upload function."""
    caplog.set_level("WARNING")

    config.spotify.spotify_client_id = "test_client_id"
    config.spotify.spotify_client_secret = "test_client_secret"
    config.spotify.spotify_redirect_uri = "test_redirect_uri"
    config.spotify.spotify_playlist_from_upload = True

    with mock.patch(
        "builtins.open",
        MockOpen(files=["spotify_playlists.yaml"], content="{}").open,
    ):
        spotify_playlist_from_upload(config)

    assert (
        caplog.records[0].message
        == "UNKNOWN - 1 - Unknown Artist.mp3 is not a valid file"
    )


@mock.patch("djtools.spotify.playlist_builder.filter_results")
@mock.patch("djtools.spotify.playlist_builder.get_spotify_client")
def test_spotify_playlist_from_upload_handles_non_match(
    _mock_spotify_client,
    mock_filter,
    config,
    caplog,
):
    """Test for the spotify_playlist_from_upload function."""
    caplog.set_level("WARNING")
    title = "Under Pressure"
    artist = "Alix Perez, T-Man"

    mock_filter.return_value = ({}, 100)
    config.spotify.spotify_playlist_from_upload = True

    with (
        mock.patch(
            "builtins.open",
            MockOpen(files=["spotify_playlists.yaml"], content="{}").open,
        ),
        mock.patch(
            "pyperclip.paste",
            return_value=f"""aweeeezy/Bass/2022-09-03: 5
 {title} - {artist}.mp3""",
        ),
    ):
        spotify_playlist_from_upload(config)

    assert caplog.records[0].message == (
        f"Could not find a match for {title} - {artist}"
    )


@mock.patch("djtools.spotify.playlist_builder.get_spotify_client")
def test_spotify_playlist_from_upload_handles_spotify_exception(
    mock_spotify_client,
    config,
    caplog,
):
    """Test for the spotify_playlist_from_upload function."""
    caplog.set_level("ERROR")
    title = "Under Pressure"
    artist = "Alix Perez, T-Man"

    mock_spotify_client.return_value.search.side_effect = Exception(
        "API Error"
    )
    config.spotify.spotify_playlist_from_upload = True
    config.spotify.spotify_client_id = "test_client_id"
    config.spotify.spotify_client_secret = "test_client_secret"
    config.spotify.spotify_redirect_uri = "test_redirect_uri"

    with (
        mock.patch(
            "builtins.open",
            MockOpen(files=["spotify_playlists.yaml"], content="{}").open,
        ),
        mock.patch(
            "pyperclip.paste",
            return_value=f"""aweeeezy/Bass/2022-09-03: 5
 {title} - {artist}.mp3""",
        ),
    ):
        spotify_playlist_from_upload(config)

    assert caplog.records[0].message.startswith(
        f'Error searching for "{title} - {artist}"'
    )


@mock.patch("pyperclip.paste", return_value="")
def test_spotify_playlist_from_upload_raises_runtimeerror(_mock_paste, config):
    """Test for the spotify_playlist_from_upload function."""
    config.spotify.spotify_playlist_from_upload = True
    with pytest.raises(
        RuntimeError,
        match="Generating a Spotify playlist from an upload requires output "
        "from an upload_music Discord webhook to be copied to the "
        "system's clipboard",
    ):
        spotify_playlist_from_upload(config)


def test_spotify_playlists(config):
    """Test for the spotify_playlists function."""
    with mock.patch(
        "djtools.spotify.playlist_builder.async_spotify_playlists"
    ) as mock_async_spotify_playlists:
        mock_async_spotify_playlists.return_value = lambda x: None
        spotify_playlists(config)
        assert mock_async_spotify_playlists.called


@mock.patch("djtools.spotify.playlist_builder.filter_results")
@mock.patch("djtools.spotify.playlist_builder.populate_playlist")
@mock.patch("djtools.spotify.playlist_builder.get_spotify_client")
@mock.patch(
    "pyperclip.paste",
    return_value="""aweeeezy/Bass/2022-09-03: 1
 A.M.C - Brazil.mp3""",
)
def test_spotify_playlist_from_upload_artist_first(
    _mock_paste,
    _mock_spotify_client,
    mock_populate,
    mock_filter,
    config,
    caplog,
):
    """Test for spotify_playlist_from_upload with artist_first=True."""
    caplog.set_level("INFO")

    mock_filter.return_value = (
        {
            "id": "some_id",
            "name": "Brazil",
            "artists": [{"name": "A.M.C"}],
        },
        100,
    )
    mock_populate.return_value = {"some-playlist": "some-id"}

    config.spotify.spotify_client_id = "test_client_id"
    config.spotify.spotify_client_secret = "test_client_secret"
    config.spotify.spotify_redirect_uri = "test_redirect_uri"
    config.spotify.spotify_playlist_from_upload = True
    config.sync.artist_first = True

    with mock.patch(
        "builtins.open",
        MockOpen(files=["spotify_playlists.yaml"], content="{}").open,
    ):
        spotify_playlist_from_upload(config)

    # Verify filter_results was called with track and artist swapped
    # (artist_first means the file is "Artist - Track" so we swap to "Track - Artist")
    mock_filter.assert_called()
    call_args = mock_filter.call_args
    # The third and fourth args should be track and artist (after swapping)
    assert call_args[0][3] == "Brazil"  # track (was artist position)
    assert call_args[0][4] == "A.M.C"  # artist (was track position)
