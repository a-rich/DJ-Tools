"""This module is used to process an audio recording.

Given a recording of multiple tracks and a Spotify playlist, use the
information from the Spotify API to:

- split the recording into individual files
- name these files with the title and artist(s)
- populate the title, artist, and album tags
- normalize the audio so the headroom is AUDIO_HEADROOM decibels
- export the files with the configured AUDIO_BITRATE and AUDIO_FORMAT
"""
from datetime import datetime
import logging

from pydub import AudioSegment, effects

from djtools.configs.config import BaseConfig
from djtools.utils.helpers import get_spotify_tracks


logger = logging.getLogger(__name__)
pydub_logger = logging.getLogger("pydub.converter")
pydub_logger.setLevel(logging.CRITICAL)


def process(config: BaseConfig):
    """Process a recording whose contents map to tracks in a Spotify playlist.

    Args:
        config: Configuration object.

    Raises:
        RuntimeError: The configured RECORDING_PLAYLIST must both exist
            in spotify_playlists.yaml and have tracks in it.
    """
    # Get the tracks of the target Spotify playlist.
    tracks = get_spotify_tracks(config, [config.RECORDING_PLAYLIST])
    if not tracks:
        raise RuntimeError(
            "There are no Spotify tracks; make sure DOWNLOAD_SPOTIFY_PLAYLIST "
            "is a key from spotify_playlists.yaml"
        )

    # Parse the relevant data from the track responses.
    track_data = []
    playlist_duration = 0
    for track in tracks[config.RECORDING_PLAYLIST]:
        # Parse release date field based on the date precision
        if track["track"]["album"]["release_date_precision"] == "year":
            date = datetime.strptime(track["track"]["album"]["release_date"], "%Y")
        elif track["track"]["album"]["release_date_precision"] == "month":
            date = datetime.strptime(track["track"]["album"]["release_date"], "%Y-%m")
        elif track["track"]["album"]["release_date_precision"] == "day":
            date = datetime.strptime(track["track"]["album"]["release_date"], "%Y-%m-%d")

        # TODO(a-rich): why won't Rekordbox load "label" and "year" tags?!
        data = {
            "album": track["track"]["album"]["name"],
            "artist": ", ".join(
                [y["name"] for y in track["track"]["artists"]]
            ),
            # NOTE: There's a 500 ms gap between tracks during playback that
            # must be accounted for.
            "duration": track["track"]["duration_ms"] + 500,
            "label": track["track"]["album"].get("label", ""),
            "title": track["track"]["name"],
            "year": str(date.year),
        }
        track_data.append(data)
        playlist_duration += data["duration"]

    # Load the audio recording and check that it's at least as long as the
    # playlist duration.
    audio = AudioSegment.from_file(config.RECORDING_FILE)
    audio_duration = len(audio)
    if audio_duration < playlist_duration:
        logger.warning(
            f"{config.RECORDING_FILE} has a duration of {audio_duration} "
            "milliseconds which is less than the sum of track lengths in the "
            f"Spotify playlist {config.RECORDING_PLAYLIST} which is "
            f"{playlist_duration} milliseconds. Please confirm your recording "
            "went as expected!"
        )

    # Iterate through the track data and export chunks of the recording.
    write_path = config.AUDIO_DESTINATION
    write_path.mkdir(parents=True, exist_ok=True)
    for track in track_data:
        # Slice the portion of the recording for the track.
        track_audio = audio[:track["duration"]]
        audio = audio[track["duration"]:]

        # Normalize the audio such that the headroom is
        # AUDIO_HEADROOM dB.
        if abs(track_audio.max_dBFS + config.AUDIO_HEADROOM) > 0.001:
            track_audio = effects.normalize(
                track_audio, headroom=config.AUDIO_HEADROOM
            )

        # Build the filename using the title, artist(s) and configured format.
        filename = (
            f'{track["artist"]} - {track["title"]}' if config.ARTIST_FIRST
            else f'{track["title"]} - {track["artist"]}'
        )
        filename = write_path / f"{filename}.{config.AUDIO_FORMAT}"

        # Warn users about malformed filenames that could break other features
        # of djtools.
        if str(filename).count(" - ") > 1:
            logger.warning(
                f'{filename} has more than one occurrence of " - "! '
                "Because djtools splits on this sequence of characters to "
                "separate track title and artist(s), you might get unexpected "
                'behavior while using features like "--check-tracks".'
            )

        # Export the audio with the configured format and bit rate with the tag
        # data collected from the Spotify response.
        track_audio.export(
            filename,
            format=config.AUDIO_FORMAT,
            bitrate=f"{config.AUDIO_BITRATE}k",
            tags={
                key: value for key, value in track.items()
                if key != "duration"
            },
        )
