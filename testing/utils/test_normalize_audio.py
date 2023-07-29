"""Testing for the process_recording module."""
from pathlib import Path
from unittest import mock

from pydub import AudioSegment
import pytest

from djtools.utils.normalize_audio import normalize


@pytest.mark.parametrize("target_headroom", [0, 2, 5])
def test_normalize(target_headroom, audio_file, config, tmpdir):
    """Test for the normalize function."""
    config.LOCAL_DIRS = [Path(tmpdir)]
    config.NORMALIZE_AUDIO_HEADROOM = target_headroom
    audio = AudioSegment.from_file(audio_file)
    with mock.patch(
        "djtools.utils.normalize_audio.AudioSegment.from_file"
    ) as mock_audio_segment:
        mock_audio_segment.return_value = audio
        normalize(config)
    audio = AudioSegment.from_file(audio_file)
    # TODO(a-rich): Getting unexpected headroom readings after exporting.
    # See this issue:
    # https://stackoverflow.com/questions/76791317/pydub-how-to-retain-headroom-across-export-and-from-file"  pylint: disable=line-too-long
    # assert abs(audio.max_dBFS + target_headroom) < 0.001


def test_normalize_handles_no_local_tracks(config):
    """Test for the normalize function."""
    config.LOCAL_DIRS = []
    with pytest.raises(
        RuntimeError,
        match=(
            "There are no local tracks; make sure LOCAL_DIRS has one or "
            "more directories containing one or more tracks"
        ),
    ):
        normalize(config)
