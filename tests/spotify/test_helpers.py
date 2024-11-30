"""Testing for the helpers module."""

import asyncio
from pathlib import Path
from unittest import mock

import pytest
import yaml

from djtools.spotify.config import SubredditConfig
from djtools.spotify.helpers import (
    _build_new_playlist,
    _catch,
    filter_results,
    _filter_tracks,
    _fuzzy_match,
    get_playlist_ids,
    get_reddit_client,
    get_spotify_client,
    get_subreddit_posts,
    _parse_title,
    populate_playlist,
    _process,
    _track_name_too_similar,
    _update_existing_playlist,
    write_playlist_ids,
)

from ..test_utils import mock_exists, MockOpen


async def _aiter(obj, num_subs):
    """Helper function for mocking asyncpraw."""
    for _ in range(num_subs):
        yield obj
        await asyncio.sleep(0.1)


@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.playlist_add_items",
    return_value=(),
)
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.user_playlist_create",
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
    """Test for the _build_new_playlist function."""
    mock_spotify.user_playlist_create.return_value = (
        mock_spotify_user_playlist_create.return_value
    )
    mock_spotify.playlist_add_items.return_value = (
        mock_spotify_playlist_add_items.return_value
    )
    new_tracks = [("test_id", "track title - artist name")]
    ret = _build_new_playlist(
        mock_spotify, "test_user", "r/techno", new_tracks
    )
    assert isinstance(ret, dict)
    assert ret == {"id": "test_id"}


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


@pytest.mark.parametrize("spotify_next_fails", [True, False])
@mock.patch(
    "djtools.spotify.helpers._filter_tracks",
    return_value=[
        (
            {
                "id": "some_id",
                "name": "Arctic Oscillations",
                "artists": [
                    {"name": "Fanu"},
                ],
            },
            100,
        )
    ],
)
@mock.patch("djtools.spotify.helpers.spotipy.Spotify")
def test_filter_results(mock_spotify, mock_filter_tracks, spotify_next_fails):
    """Test for the filter_results function."""
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
    mock_spotify.next.return_value = mock_filter_tracks.return_value
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
    expected = (
        {
            "id": "some_id",
            "name": "Arctic Oscillations",
            "artists": [
                {"name": "Fanu"},
            ],
        },
        100,
    )
    assert ret == expected


def test_filter_tracks():
    """Test for the _filter_tracks function."""
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
    ret = _filter_tracks(tracks, threshold, title, artist)
    expected = [
        (
            {
                "name": title,
                "artists": [
                    {"name": artist},
                ],
            },
            threshold * 2,
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
    """Test for the _fuzzy_match function."""
    mock_spotify.search.return_value = mock_spotify_search.return_value
    threshold = 100
    with (
        mock.patch(
            "djtools.spotify.helpers._parse_title",
            return_value=title,
        ),
        mock.patch(
            "djtools.spotify.helpers.filter_results",
            return_value=(
                (
                    {
                        "id": "some_id",
                        "name": "Arctic Oscillations",
                        "artists": [
                            {"name": "Fanu"},
                        ],
                    },
                    100,
                )
                if match_result
                else (None, 0)
            ),
        ) as mock_filter_results,
    ):
        ret = _fuzzy_match(mock_spotify, title, threshold)
    if not all(x for x in title):
        # If a track title AND artist name aren't resolved, then None is
        # returned.
        assert not ret
    if not match_result:
        # If no matches are found, then None is returned.
        assert not ret
    if match_result and all(x for x in title):
        # If no matches are found, then None is returned.
        assert isinstance(ret, tuple)
        id_, match = ret
        expected_ret = mock_filter_results.return_value[0]
        assert id_ == expected_ret["id"]
        artists = ", ".join([y["name"] for y in expected_ret["artists"]])
        assert match == f'{expected_ret["name"]} - {artists}'


@mock.patch("djtools.spotify.helpers.get_spotify_client")
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.search", side_effect=Exception()
)
def test_fuzzy_match_handles_spotify_exception(
    mock_spotify_search, mock_spotify, caplog
):
    """Test for the _fuzzy_match function."""
    caplog.set_level("ERROR")
    mock_spotify.search.side_effect = mock_spotify_search.side_effect
    threshold = 100
    title = "Arctic Oscillations"
    artist = "Fanu"
    with mock.patch(
        "djtools.spotify.helpers._parse_title",
        return_value=(title, artist),
    ):
        ret = _fuzzy_match(mock_spotify, title, threshold)
        assert caplog.records[0].message.startswith(
            f'Error searching for "{title} - {artist}"'
        )
        assert not ret


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
            [
                ("spotify_playlists.yaml", config_exists),
            ],
            path,
        ),
    ):
        playlist_ids = get_playlist_ids()
    assert isinstance(playlist_ids, dict)
    assert playlist_ids == expected


@mock.patch("djtools.spotify.helpers.praw.Reddit")
def test_get_reddit_client(config):
    """Test for the get_reddit_client function."""
    config.reddit_client_id = "test_client_id"
    config.reddit_client_secret = "test_client_secret"
    config.reddit_user_agent = "test_user_agent"
    get_reddit_client(config)


@mock.patch("djtools.spotify.helpers.spotipy.Spotify")
def test_get_spotify_client(config):
    """Test for the get_spotify_client function."""
    config.spotify_client_id = "test_client_id"
    config.spotify_client_secret = "test_client_secret"
    config.spotify_redirect_uri = "test_redirect_uri"
    get_spotify_client(config)


@pytest.mark.asyncio
@pytest.mark.parametrize("subreddit_type", ["hot", "top"])
@pytest.mark.parametrize("num_subs", [5, 0])
@mock.patch("djtools.spotify.helpers.praw.Reddit.close", mock.Mock())
@mock.patch("djtools.spotify.helpers._process")
@mock.patch("djtools.spotify.helpers.praw.models.Submission")
@mock.patch("djtools.spotify.helpers.praw.Reddit")
@mock.patch("djtools.spotify.helpers.get_spotify_client")
async def test_get_subreddit_posts(
    mock_spotify,
    mock_praw,
    mock_praw_submission,
    mock_process,
    subreddit_type,
    num_subs,
    config,
    caplog,
):
    """Test for the get_subreddit_posts function."""
    caplog.set_level("INFO")
    subreddit = SubredditConfig(
        name="techno", type=subreddit_type
    ).model_dump()
    praw_cache = {}
    mock_praw_submission.id = "test_id"
    mock_process.return_value = "track - artist"
    with (
        mock.patch(
            "djtools.spotify.helpers._catch",
        ) as mock_catch,
        mock.patch(
            "djtools.spotify.helpers.praw.Reddit.subreddit",
            new=mock.AsyncMock(),
        ),
    ):
        mock_catch.return_value = _aiter(mock_praw_submission, num_subs)
        await get_subreddit_posts(
            mock_spotify, mock_praw, subreddit, config, praw_cache
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
@mock.patch("djtools.spotify.helpers.spotipy.Spotify.playlist")
@mock.patch("djtools.spotify.helpers._build_new_playlist")
@mock.patch("djtools.spotify.helpers._update_existing_playlist")
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
    """Test for the populate_playlist function."""
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
    # If there are tracks to add and the playlist to add them to exists
    # already, then a call to _update_existing_playlist is expected.
    if playlist_ids and tracks:
        assert mock_update_existing_playlist.call_count == 1
    # If there are tracks to add and the playlist to add them to does NOT exist
    # already, then a call to _build_new_playlist is expected.
    elif tracks:
        assert caplog.records.pop(0).message == (
            f"Unable to get ID for {playlist_name}...creating a new playlist"
        )
        assert mock_build_new_playlist.call_count == 1
        assert playlist_name in ret_playlist_ids
    # Even if there are no tracks being added, an existing playlist must have
    # it's data retrieved for displaying info.
    elif playlist_ids:
        assert mock_spotify_playlist.call_count == 1

    # If the playlist doesn't exist already AND there are no tracks, then
    # nothing should happen.
    if not (playlist_ids or tracks):
        assert (
            mock_update_existing_playlist.call_count
            == mock_build_new_playlist.call_count
            == mock_spotify_playlist.call_count
            == 0
        )
        assert len(caplog.records) == 0
    # Whether a new playlist was created or an existing one updated, the
    # playlist name and URL must be displayed.
    else:
        assert caplog.records.pop(0).message == (
            f'"{ret_val["name"]}": {ret_val["external_urls"].get("spotify")}'
        )


@pytest.mark.parametrize(
    "url",
    [
        "https://open.spotify.com/track/1lps8esDJ9M6rG3HBjhuux",
        "https://some-other-url.com/some_id",
    ],
)
@mock.patch("djtools.spotify.helpers.get_spotify_client")
@mock.patch(
    "djtools.spotify.helpers.praw.models.Submission",
    new_callable=mock.AsyncMock,
)
def test_process(mock_praw_submission, mock_spotipy, url):
    """Test for the _process function."""
    title = "Arctic Oscillations - Fanu"
    mock_praw_submission.url = url
    mock_praw_submission.title = title
    with mock.patch(
        "djtools.spotify.helpers._fuzzy_match", return_value=(url, title)
    ):
        ret = _process(mock_praw_submission, mock_spotipy, 50)
    assert isinstance(ret, tuple)
    assert ret == (url, title)


@pytest.mark.parametrize(
    "playlist_track_names",
    [
        ["Arctic Oscillations - Fanu"],
        ["Not a Match - Some Artist"],
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
        assert caplog.records[0].message == (
            f'Candidate new track "{track}" is too similar to existing '
            f'track "{playlist_track_names[0]}"'
        )


@pytest.mark.parametrize("too_similar", [True, False])
@mock.patch(
    "djtools.spotify.helpers._track_name_too_similar",
    return_value=None,
)
@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.playlist_add_items",
    return_value=(),
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
    too_similar,
    caplog,
):
    """Test for the _update_existing_playlist function."""
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
    mock_track_name_too_similar.return_value = too_similar
    playlist = ""
    new_tracks = [
        ("test_id", "test track"),
        ("unique_id", "another track"),
        ("https://open.spotify.com/track/1lps8esDJ9M6rG3HBjhuux", "a track"),
    ]
    limit = 1
    verbosity = 1
    ret = _update_existing_playlist(
        mock_spotify, playlist, new_tracks, limit, verbosity
    )
    assert isinstance(ret, dict)
    assert caplog.records[0].message == (
        'Candidate new track "test track" is already in the playlist'
    )


@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.next",
    side_effect=[
        {
            "tracks": {
                "next": True,
            },
            "items": [
                {
                    "track": {
                        "uri": "test_uri",
                        "id": "test_id",
                        "name": "last track title",
                        "artists": [{"name": "final artist name"}],
                    },
                },
            ],
        },
        {
            "tracks": {},
            "items": [],
        },
    ],
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
                        "artists": [{"name": "final artist name"}],
                    },
                },
            ],
            "next": True,
        },
    },
)
@mock.patch("djtools.spotify.helpers.get_spotify_client")
def test_update_existing_playlist_keyerror_handling(
    mock_spotify,
    mock_spotify_playlist,
    mock_spotify_next,
    caplog,
):
    """Test for KeyError exception handling in _update_existing_playlist."""
    caplog.set_level("ERROR")

    mock_spotify.playlist.return_value = mock_spotify_playlist.return_value
    mock_spotify.next.return_value = mock_spotify_next.return_value
    mock_spotify.next.side_effect = mock_spotify_next.side_effect

    playlist = ""
    new_tracks = [("test_id", "test track")]
    limit = 1
    verbosity = 1

    ret = _update_existing_playlist(
        mock_spotify, playlist, new_tracks, limit, verbosity
    )

    assert isinstance(ret, dict)
    assert len(caplog.records) == 0
    # assert "Failed to get tracks from playlist" in caplog.records[0].message


@mock.patch(
    "djtools.spotify.helpers.spotipy.Spotify.next",
    side_effect=Exception("Some random exception"),
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
def test_update_existing_playlist_general_exception_handling(
    mock_spotify,
    mock_spotify_playlist,
    mock_spotify_next,
    caplog,
):
    """Test for general exception handling in _update_existing_playlist."""
    caplog.set_level("ERROR")
    mock_spotify.playlist.return_value = mock_spotify_playlist.return_value
    mock_spotify.next.return_value = mock_spotify_next.return_value
    mock_spotify.next.side_effect = Exception("Some random exception")

    playlist = ""
    new_tracks = [
        ("test_id", "test track"),
    ]
    limit = 1
    verbosity = 1

    ret = _update_existing_playlist(
        mock_spotify, playlist, new_tracks, limit, verbosity
    )

    assert isinstance(ret, dict)
    assert len(caplog.records) > 0
    assert "Some random exception" in caplog.records[0].message


def test_write_playlist_ids():
    """Test for the write_playlist_ids function."""
    ids_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "djtools"
        / "configs"
        / "spotify_playlists.yaml"
    )

    # Mock a single playlist as contents.
    with mock.patch(
        "builtins.open",
        MockOpen(
            files=["spotify_playlists.yaml"],
            content="playlist: playlist-id",
        ).open,
    ):
        with open(ids_path, mode="r", encoding="utf-8") as _file:
            data = yaml.load(_file, Loader=yaml.FullLoader)
    expected = {"playlist": "playlist-id"}
    assert data == expected

    # Write a new playlist to the config.
    expected2 = {**expected, **{"another-playlist": "different-playlist-id"}}
    write_playlist_ids(expected2)
    with open(ids_path, mode="r", encoding="utf-8") as _file:
        data = yaml.load(_file, Loader=yaml.FullLoader)

    # Assert config contains both old data and new data.
    assert data == expected2

    # Remove config file written by test.
    ids_path.unlink()
