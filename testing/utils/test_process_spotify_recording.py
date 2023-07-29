"""Testing for the process_recording module."""
from pathlib import Path
from unittest import mock

from pydub import AudioSegment
import pytest

from djtools.utils.process_recording import process


@mock.patch("djtools.utils.process_recording.get_spotify_tracks")
@mock.patch(
    "djtools.utils.process_recording.AudioSegment.from_file",
    mock.Mock(return_value=AudioSegment.silent(duration=30000)),
)
def test_process(mock_get_spotify_tracks, config, tmpdir):
    """Test for the process function."""
    mock_get_spotify_tracks.return_value = {
        "playlist": [
            {
                "track": {
                    "album": {
                        "name": "",
                        "release_date_precision": "year",
                        "release_date": "2023",
                        "label": "",
                    },
                    "artists": [{"name": "some artist"}],
                    "duration_ms": 10000,
                    "name": "some name",
                },
            },
            {
                "track": {
                    "album": {
                        "name": "",
                        "release_date_precision": "month",
                        "release_date": "2023-07",
                        "label": "",
                    },
                    "artists": [
                        {"name": "another artist"},
                        {"name": "a final artist"},
                    ],
                    "duration_ms": 10000,
                    "name": "another name",
                },
            },
            {
                "track": {
                    "album": {
                        "name": "",
                        "release_date_precision": "day",
                        "release_date": "2023-07-28",
                        "label": "",
                    },
                    "artists": [
                        {"name": "another artist"},
                        {"name": "a final artist"},
                    ],
                    "duration_ms": 10000,
                    "name": "a final name",
                },
            },
        ],
    }
    config.USB_PATH = Path(tmpdir)
    config.RECORDING_FILE= "file.mp3"
    config.RECORDING_PLAYLIST = "playlist"
    process(config)
    output_files = list((config.USB_PATH / "DJ Music" / "New Music").iterdir())
    assert (
        len(output_files) == len(
            mock_get_spotify_tracks.return_value["playlist"]
        )
    )


@mock.patch(
    "djtools.utils.process_recording.get_spotify_tracks",
    mock.Mock(return_value={}),
)
@mock.patch(
    "djtools.utils.process_recording.AudioSegment.export", mock.Mock()
)
def test_process_handles_missing_or_empty_playlist(config):
    """Test for the process function."""
    config.RECORDING_PLAYLIST = "playlist"
    with pytest.raises(
        RuntimeError,
        match=(
            "There are no Spotify tracks; make sure "
            "DOWNLOAD_SPOTIFY_PLAYLIST is a key from "
            "spotify_playlists.yaml"
        ),
    ):
        process(config)


@mock.patch("djtools.utils.process_recording.get_spotify_tracks")
@mock.patch("djtools.utils.process_recording.AudioSegment.from_file")
@mock.patch(
    "djtools.utils.process_recording.AudioSegment.export", mock.Mock()
)
def test_process_warns_when_recording_is_too_short(
    mock_audio_segment, mock_spotify_tracks, config, caplog, tmpdir
):
    """Test for the process function."""
    config.RECORDING_FILE= "file.mp3"
    config.RECORDING_PLAYLIST = "playlist"
    config.USB_PATH = Path(tmpdir)
    caplog.set_level("WARNING")
    mock_audio_segment.return_value = AudioSegment.silent(duration=90_000)
    mock_spotify_tracks.return_value = {
        "playlist": [
            {
                "track": {
                    "album": {
                        "name": "",
                        "release_date_precision": "year",
                        "release_date": "2023",
                        "label": "",
                    },
                    "artists": [{"name": "artist"}],
                    "duration_ms": 90_001,
                    "name": "some - bad name",
                },
            },
        ],
    }
    audio_duration = len(mock_audio_segment.return_value)
    playlist_duration = sum(
        (
            track["track"]["duration_ms"] + 500
            for playlist in mock_spotify_tracks.return_value.values()
            for track in playlist
        )
    )
    process(config)
    assert caplog.records[0].message == (
        f"file.mp3 has a duration of {audio_duration} milliseconds which is "
        "less than the sum of track lengths in the Spotify playlist playlist "
        f"which is {playlist_duration} milliseconds. Please confirm your "
        "recording went as expected!"
    )



@mock.patch(
    "djtools.utils.process_recording.get_spotify_tracks",
    mock.Mock(
        return_value={
            "playlist": [
                {
                    "track": {
                        "album": {
                            "name": "",
                            "release_date_precision": "year",
                            "release_date": "2023",
                            "label": "",
                        },
                        "artists": [{"name": "artist"}],
                        "duration_ms": 1000,
                        "name": "some - bad name",
                    },
                }
            ],
        },
    ),
)
@mock.patch(
    "djtools.utils.process_recording.AudioSegment.from_file",
    mock.Mock(return_value=AudioSegment.silent(duration=2000)),
)
@mock.patch(
    "djtools.utils.process_recording.AudioSegment.export", mock.Mock()
)
def test_process_warns_when_filename_is_malformed(
    config, caplog, tmpdir
):
    """Test for the process function."""
    config.RECORDING_PLAYLIST = "playlist"
    config.USB_PATH = Path(tmpdir)
    caplog.set_level("WARNING")
    process(config)
    filename = (
        tmpdir / "DJ Music" / "New Music" / "some - bad name - artist.mp3"
    )
    assert caplog.records[0].message == (
        f'{filename} has at more than one occurrence of " - "! '
        "Because djtools splits on this sequence of characters to "
        "separate track title and artist(s), you might get unexpected "
        'behavior while using features like "--check-tracks".'
    )
