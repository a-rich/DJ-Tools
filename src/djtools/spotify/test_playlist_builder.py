import os
from unittest import mock

import pyperclip
import pytest

from djtools.spotify.playlist_builder import (
    async_update_auto_playlists,
    playlist_from_upload,
    update_auto_playlists,
)
from test_data import MockOpen


pytest_plugins = [
    "test_data",
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "playlist_subreddits",
    [[], [{"name": "jungle", "type": "hot", "period": "week", "limit": 50}]],
)
@pytest.mark.parametrize("got_playlist_ids", [True, False])
@pytest.mark.parametrize("got_tracks", [True, False])
@mock.patch("os.path.exists", return_value=True)
@mock.patch(
    "djtools.spotify.helpers.update_existing_playlist",
    return_value={
        "name": "test_playlist",
        "external_urls": {"spotify": "https://test-url.com"},
        "id": "test-id",
    },
)
@mock.patch(
    "djtools.spotify.helpers.build_new_playlist",
    return_value={
        "name": "test_playlist",
        "external_urls": {"spotify": "https://test-url.com"},
        "id": "test-id",
    },
)
@mock.patch(
    "djtools.spotify.playlist_builder.get_subreddit_posts",
    return_value=[
        [("track-id", "track name")],
        {"name": "jungle", "type": "hot", "period": "week", "limit": 50},
    ],
)
@mock.patch("djtools.spotify.playlist_builder.get_spotify_client")
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
            files=["spotify_playlists.json", ".praw.cache"],
            content='{"jungle": "some-id"}' if got_playlist_ids else "{}",
        ).open
    ):
        await async_update_auto_playlists(test_config)


@pytest.mark.asyncio
@mock.patch(
    "djtools.spotify.playlist_builder.get_subreddit_posts",
    return_value=(
        [("track-id", "track name")],
        {"name": "jungle", "type": "hot", "period": "week", "limit": 50},
    ),
)
@mock.patch("djtools.spotify.playlist_builder.get_spotify_client")
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
        match="The spotify.playlist_builder module requires the config option "
            "SPOTIFY_USERNAME"
    ):
        await async_update_auto_playlists(test_config)


@pytest.mark.asyncio
async def test_async_update_auto_playlists_missing_playlists(test_config, caplog):
    caplog.set_level("ERROR")
    test_config["AUTO_PLAYLIST_SUBREDDITS"] = ""
    ret = await async_update_auto_playlists(test_config)
    assert not ret
    assert caplog.records[0].message == (
        "Using the spotify.playlist_builder module requires the config "
        "option AUTO_PLAYLIST_SUBREDDITS"
    )


@pytest.mark.parametrize("input_", [True, "test.txt"])
@mock.patch(
    "djtools.spotify.playlist_builder.filter_results",
    return_value={
        "id": "some_id",
        "name": "some_name",
        "artists": [ 
            {"name": "some_artist"},
        ],
    }
)
@mock.patch(
    "djtools.spotify.playlist_builder.populate_playlist",
    return_value={"some-playlist": "some-id"},
)
@mock.patch("djtools.spotify.playlist_builder.get_spotify_client")
def test_playlist_from_upload(
    mock_spotify,
    mock_populate_playlist,
    mock_filter_results,
    input_,
    test_config,
    tmpdir,
):
    test_config["SPOTIFY_CLIENT_ID"] = "test_client_id"
    test_config["SPOTIFY_CLIENT_SECRET"] = "test_client_secret"
    test_config["SPOTIFY_REDIRECT_URI"] = "test_redirect_uri"
    content = """aweeeezy/Bass/2022-09-03: 5
                   Brazil - A.M.C.mp3
                   Endless Haze - Koherent.mp3
                   Two Rangers - Two Rangers.mp3
                   Under Pressure - Alix Perez, T-Man.mp3
                   zoom.1 - Relativity Lounge, wicker's portal.mp3
                  aweeeezy/House/2022-09-03: 2
                   Shirt - Cour T..mp3
                   UNKNOWN - 1 - Unknown Artist.mp3"""
    if isinstance(input_, bool):
        pyperclip.copy(content)
        test_config["PLAYLIST_FROM_UPLOAD"] = True
    else:
        path = os.path.join(tmpdir, input_).replace(os.sep, "/")
        with open(path, mode="w", encoding="utf-8",) as _file:
            _file.write(content)
        test_config["PLAYLIST_FROM_UPLOAD"] = path
    with mock.patch(
        "builtins.open",
        MockOpen(files=["spotify_playlists.json"], content="{}").open
    ):
        playlist_from_upload(test_config)


def test_playlist_from_upload_raises_playlist_from_upload_keyerror(
    test_config
):
    del test_config["PLAYLIST_FROM_UPLOAD"]
    with pytest.raises(
        KeyError,
        match="Using the playlist_from_upload function of the "
            "spotify.playlist_builder module requires the "
            "PLAYLIST_FROM_UPLOAD config option",
    ):
        playlist_from_upload(test_config)


def test_playlist_from_upload_raises_filenotfounderror(test_config):
    file_ = "nonexistent.txt"
    test_config["PLAYLIST_FROM_UPLOAD"] = file_
    with pytest.raises(FileNotFoundError, match=f"{file_} does not exit"):
        playlist_from_upload(test_config)


def test_playlist_from_upload_raises_runtimeerror(test_config):
    pyperclip.copy("")
    test_config["PLAYLIST_FROM_UPLOAD"] = True
    with pytest.raises(
        RuntimeError,
        match="Generating a Spotify playlist from an upload requires either "
            '"upload_output", a path to the upload_music Discord webhook '
            "output, or that output to be copied to the system's clipboard"
    ):
        playlist_from_upload(test_config)


def test_playlist_from_upload_raises_username_keyerror(test_config):
    del test_config["SPOTIFY_USERNAME"]
    test_config["PLAYLIST_FROM_UPLOAD"] = True
    pyperclip.copy(" ")
    with pytest.raises(
        KeyError,
        match="The spotify.playlist_builder module requires the config option "
            "SPOTIFY_USERNAME"
    ):
        playlist_from_upload(test_config)


def test_playlist_from_upload_raises_valueerror(test_config):
    upload_output = 1
    test_config["PLAYLIST_FROM_UPLOAD"] = upload_output
    with pytest.raises(
        ValueError,
        match="Config option PLAYLIST_FROM_UPLOAD must be either a path to a "
            f'file or a boolean, but got "{upload_output}"'
    ):
        playlist_from_upload(test_config)


@mock.patch("djtools.spotify.helpers.get_spotify_client")
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.search",
    side_effect=Exception()
)
def test_playlist_from_upload_handles_spotify_exception(
    mock_spotify_search, mock_spotify, test_config, caplog
):
    caplog.set_level("ERROR")
    mock_spotify.return_value.search.side_effect = (
        mock_spotify_search.side_effect
    )
    title = "Under Pressure"
    artist = "Alix Perez, T-Man"
    content = f"""aweeeezy/Bass/2022-09-03: 5
                   {title} - {artist}.mp3"""
    pyperclip.copy(content)
    test_config["PLAYLIST_FROM_UPLOAD"] = True
    test_config["SPOTIFY_CLIENT_ID"] = "test_client_id"
    test_config["SPOTIFY_CLIENT_SECRET"] = "test_client_secret"
    test_config["SPOTIFY_REDIRECT_URI"] = "test_redirect_uri"
    with mock.patch(
        "builtins.open",
        MockOpen(files=["spotify_playlists.json"], content="{}").open
    ):
        playlist_from_upload(test_config)
    assert caplog.records[0].message.startswith(
        f'Error searching for "{title} - {artist}"'
    )


@mock.patch(
    "djtools.spotify.playlist_builder.filter_results",
    return_value={},
)
@mock.patch("djtools.spotify.playlist_builder.get_spotify_client")
def test_playlist_from_upload_handles_non_match(
    mock_spotify, mock_filter_results, test_config, caplog
):
    caplog.set_level("WARNING")
    title = "Under Pressure"
    artist = "Alix Perez, T-Man"
    content = f"""aweeeezy/Bass/2022-09-03: 5
                   {title} - {artist}.mp3"""
    pyperclip.copy(content)
    test_config["PLAYLIST_FROM_UPLOAD"] = True
    with mock.patch(
        "builtins.open",
        MockOpen(files=["spotify_playlists.json"], content="{}").open
    ):
        playlist_from_upload(test_config)
    assert caplog.records[0].message == (
        f"Could not find a match for {title} - {artist}"
    )


@mock.patch(
    "djtools.spotify.playlist_builder.async_update_auto_playlists",
    return_value=lambda x: None,
)
def test_update_auto_playlists(
    mock_async_update_auto_playlists, test_config
):
    update_auto_playlists(test_config)
