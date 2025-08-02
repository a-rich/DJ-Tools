"""Testing for the process_recording module."""

from pathlib import Path
from unittest import mock

import pytest

from djtools.utils.normalize_audio import normalize


def test_normalize_handles_no_local_tracks(config):
    """Test for the normalize function."""
    config.utils.local_dirs = []
    with pytest.raises(
        RuntimeError,
        match=(
            "There are no local tracks; make sure local_dirs has one or "
            "more directories containing one or more tracks"
        ),
    ):
        normalize(config)


def test_normalize_handles_decode_error(config, tmpdir, caplog):
    """Test for the normalize function."""
    caplog.set_level("ERROR")
    tmpdir = Path(tmpdir)
    filename = tmpdir / "bad_audio_file.txt"
    filename.write_text("something")
    config.utils.local_dirs = [tmpdir]
    normalize(config)
    assert caplog.records[0].message.startswith(f"Couldn't decode {filename}:")


@pytest.mark.parametrize("target_headroom", [0, 2, 5])
@mock.patch("djtools.utils.normalize_audio.effects.normalize")
@mock.patch("djtools.utils.process_recording.AudioSegment.export", mock.Mock())
def test_normalize(
    mock_normalize, target_headroom, audio_file, config, input_tmpdir
):
    """Test for the normalize function."""
    config.utils.audio_headroom = target_headroom
    audio, _ = audio_file
    file_path = Path(input_tmpdir) / "file.wav"
    with (
        mock.patch(
            "djtools.utils.normalize_audio.AudioSegment.from_file"
        ) as mock_audio_segment,
        mock.patch(
            "djtools.utils.normalize_audio.get_local_tracks",
            mock.Mock(return_value={"playlist": [file_path]}),
        ),
    ):
        mock_audio_segment.return_value = audio
        normalize(config)
        if abs(audio.max_dBFS + target_headroom) > 0.001:
            mock_normalize.assert_called_once()
    # TODO(a-rich): Getting unexpected headroom readings after exporting.
    # See this issue:
    # https://stackoverflow.com/questions/76791317/pydub-how-to-retain-headroom-across-export-and-from-file"  pylint: disable=line-too-long
    # audio = AudioSegment.from_file(_file)
    # assert abs(audio.max_dBFS + target_headroom) < 0.001


@mock.patch(
    "djtools.utils.normalize_audio.utils.mediainfo",
    mock.Mock(side_effect=FileNotFoundError()),
)
@mock.patch("djtools.utils.normalize_audio.effects.normalize", mock.Mock())
@mock.patch("djtools.utils.process_recording.AudioSegment.export", mock.Mock())
def test_normalize_handles_missing_ffmpeg(
    config, audio_file, input_tmpdir, caplog
):
    """Test for the normalize function."""
    caplog.set_level("WARNING")
    config.utils.audio_headroom = 0.0
    audio, _ = audio_file
    with (
        mock.patch(
            "djtools.utils.normalize_audio.AudioSegment.from_file"
        ) as mock_audio_segment,
        mock.patch(
            "djtools.utils.normalize_audio.get_local_tracks",
            mock.Mock(
                return_value={"playlist": [Path(input_tmpdir) / "file.wav"]}
            ),
        ),
    ):
        mock_audio_segment.return_value = audio
        normalize(config)
        assert caplog.records[0].message.startswith(
            'Couldn\'t export file with ID3 tags; ensure "ffmpeg" is installed'
        )
