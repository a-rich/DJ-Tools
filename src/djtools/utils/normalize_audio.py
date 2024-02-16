"""This module is used to normalize audio files in one or more directories.
"""

import logging

from pydub import AudioSegment, effects, utils

from djtools.configs.config import BaseConfig
from djtools.utils.helpers import get_local_tracks


logger = logging.getLogger(__name__)
pydub_logger = logging.getLogger("pydub.converter")
pydub_logger.setLevel(logging.CRITICAL)


def normalize(config: BaseConfig):
    """Gets local tracks and normalizes them.

    Tracks will be overwritten and have a headroom equal to AUDIO_HEADROOM.

    Args:
        config: Configuration object.

    Raises:
        RuntimeError: Must have local tracks to normalize.
    """
    folder_tracks = get_local_tracks(config)
    if not folder_tracks:
        raise RuntimeError(
            "There are no local tracks; make sure LOCAL_DIRS has one or "
            "more directories containing one or more tracks"
        )

    for track in [
        track
        for tracks in folder_tracks.values()
        for track in tracks
        if track.is_file() and not track.name.startswith(".")
    ]:
        try:
            audio = AudioSegment.from_file(track)
        except Exception as exc:
            logger.error(f"Couldn't decode {track}: {exc}")
            continue

        if abs(audio.max_dBFS + config.AUDIO_HEADROOM) > 0.001:
            logger.info(
                f"{track} has a max dB of {audio.max_dBFS}, normalizing to "
                f"have a headroom of {config.AUDIO_HEADROOM}..."
            )
            try:
                tags = utils.mediainfo(track).get("TAG", {})
            except FileNotFoundError as exc:
                logger.warning(
                    f"Couldn't export {track.stem} with ID3 tags; ensure "
                    f'"ffmpeg" is installed: {exc}'
                )
                tags = {}
            audio = effects.normalize(audio, headroom=config.AUDIO_HEADROOM)
            audio.export(
                track.parent / f"{track.stem}.{config.AUDIO_FORMAT}",
                tags=tags,
                bitrate=f"{config.AUDIO_BITRATE}k",
                format=config.AUDIO_FORMAT,
            )
            continue
