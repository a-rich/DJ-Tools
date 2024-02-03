"""Testing for the process_recording module."""

from pathlib import Path
from unittest import mock

from pydub import AudioSegment
import pytest

from djtools.utils.process_recording import process


@mock.patch(
    "djtools.utils.process_recording.get_spotify_tracks",
    mock.Mock(return_value={}),
)
@mock.patch("djtools.utils.helpers.AudioSegment.export", mock.Mock())
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


@mock.patch("djtools.utils.helpers.AudioSegment.export", mock.Mock())
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
                        "artists": [{"name": "some artist"}],
                        "duration_ms": 10000,
                        "name": "some name",
                    },
                },
            ]
        }
    ),
)
@mock.patch(
    "djtools.utils.process_recording.AudioSegment.from_file",
    mock.Mock(return_value=AudioSegment.silent(duration=2000)),
)
@mock.patch("djtools.utils.process_recording.process_parallel", mock.Mock())
@mock.patch("djtools.utils.process_recording.trim_initial_silence")
@pytest.mark.parametrize("trim,expected", [(0, 0), (1, 1), ("auto", 1)])
def test_process_skips_trimming_initial_silence(
    mock_trim_initial_silence, trim, expected, config, tmpdir
):
    """Test for the process function."""
    config.AUDIO_DESTINATION = Path(tmpdir)
    config.RECORDING_FILE = "file.wav"
    config.RECORDING_PLAYLIST = "playlist"
    config.TRIM_INITIAL_SILENCE = trim
    process(config)
    assert mock_trim_initial_silence.call_count == expected


@mock.patch("djtools.utils.helpers.AudioSegment.export", mock.Mock())
@mock.patch("djtools.utils.process_recording.get_spotify_tracks")
@mock.patch("djtools.utils.process_recording.AudioSegment.from_file")
def test_process_warns_when_recording_is_too_short(
    mock_audio_segment, mock_spotify_tracks, config, caplog, tmpdir
):
    """Test for the process function."""
    config.RECORDING_FILE = "file.wav"
    config.RECORDING_PLAYLIST = "playlist"
    config.AUDIO_DESTINATION = Path(tmpdir)
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
        f"file.wav has a duration of {audio_duration} milliseconds which is "
        "less than the sum of track lengths in the Spotify playlist playlist "
        f"which is {playlist_duration} milliseconds. Please confirm your "
        "recording went as expected!"
    )


@mock.patch("djtools.utils.helpers.AudioSegment.export", mock.Mock())
@mock.patch("djtools.utils.helpers.effects.normalize", mock.Mock())
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
def test_process_warns_when_filename_is_malformed(config, tmpdir, caplog):
    """Test for the process function."""
    caplog.set_level("WARNING")
    config.RECORDING_PLAYLIST = "playlist"
    config.AUDIO_DESTINATION = Path(tmpdir)
    process(config)
    filename = tmpdir / "some - bad name - artist.mp3"
    assert caplog.records[0].message == (
        f'{filename} has more than one occurrence of " - "! '
        "Because djtools splits on this sequence of characters to "
        "separate track title and artist(s), you might get unexpected "
        'behavior while using features like "--check-tracks".'
    )


@mock.patch("djtools.utils.helpers.AudioSegment.export")
@mock.patch("djtools.utils.helpers.effects.normalize")
@mock.patch("djtools.utils.process_recording.AudioSegment.from_file")
@mock.patch("djtools.utils.process_recording.get_spotify_tracks")
def test_process(
    mock_get_spotify_tracks,
    mock_audio,
    mock_normalize,
    mock_export,
    config,
    tmpdir,
):
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
    mock_audio.return_value = AudioSegment.silent(duration=30000)
    mock_normalize.return_value = mock_audio.return_value

    def mock_export_function(
        filename, **kwargs
    ):  # pylint: disable=unused-argument
        with open(filename, mode="wb") as _file:
            _file.write(b"")

    mock_export.side_effect = mock_export_function
    config.AUDIO_DESTINATION = Path(tmpdir)
    config.RECORDING_FILE = "file.wav"
    config.RECORDING_PLAYLIST = "playlist"
    process(config)
    track_count = len(mock_get_spotify_tracks.return_value["playlist"])
    assert mock_export.call_count == track_count
    assert mock_normalize.call_count == track_count
    assert len(list(config.AUDIO_DESTINATION.iterdir())) == track_count
