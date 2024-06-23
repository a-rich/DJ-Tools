"""This module is used to process an audio recording.

Given a recording of multiple tracks and a Spotify playlist, use the
information from the Spotify API to:

- split the recording into individual files
- name these files with the title and artist(s)
- populate the title, artist, and album tags
- normalize the audio so the headroom is AUDIO_HEADROOM decibels
- export the files with the configured AUDIO_BITRATE and AUDIO_FORMAT
"""

from concurrent.futures import as_completed, ThreadPoolExecutor
from datetime import datetime
import logging
import os

from pydub import AudioSegment
from tqdm import tqdm

from djtools.configs.config import BaseConfig
from djtools.utils.helpers import (
    get_spotify_tracks,
    process_parallel,
    trim_initial_silence,
)


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
        date_year = ""
        release_date = track["track"]["album"]["release_date"]
        release_precision = track["track"]["album"]["release_date_precision"]
        if release_precision == "year":
            date_year = datetime.strptime(release_date, "%Y").year
        elif release_precision == "month":
            date_year = datetime.strptime(release_date, "%Y-%m").year
        elif release_precision == "day":
            date_year = datetime.strptime(release_date, "%Y-%m-%d").year

        # TODO(a-rich): Why won't Rekordbox load "label" and "year" tags?!
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
            "year": date_year,
        }
        track_data.append(data)
        playlist_duration += data["duration"]

    # Load the audio and trim the initial silence.
    logger.info("Loading audio...")
    audio = AudioSegment.from_file(config.RECORDING_FILE)
    if config.TRIM_INITIAL_SILENCE:
        audio = trim_initial_silence(
            audio,
            [track["duration"] for track in track_data],
            config.TRIM_INITIAL_SILENCE,
        )

    # Check that the audio is at least as long as the playlist duration.
    audio_duration = len(audio)
    if audio_duration < playlist_duration:
        logger.warning(
            f"{config.RECORDING_FILE} has a duration of {audio_duration} "
            "milliseconds which is less than the sum of track lengths in the "
            f"Spotify playlist {config.RECORDING_PLAYLIST} which is "
            f"{playlist_duration} milliseconds. Please confirm your recording "
            "went as expected!"
        )

    # Create destination for exported audio.
    write_path = config.AUDIO_DESTINATION
    write_path.mkdir(parents=True, exist_ok=True)

    # Split recording into the individual tracks.
    audio_chunks = []
    for track in track_data:
        track_audio = audio[: track["duration"]]
        audio = audio[track["duration"] :]
        audio_chunks.append(track_audio)

    # Normalize audio and export tracks with tags.
    payload = zip(
        [config] * len(audio_chunks),
        audio_chunks,
        track_data,
        [write_path] * len(audio_chunks),
    )

    with ThreadPoolExecutor(
        max_workers=os.cpu_count() * 4  # pylint: disable=no-member
    ) as executor:
        futures = [
            executor.submit(process_parallel, *args) for args in payload
        ]

        with tqdm(total=len(futures), desc="Exporting tracks") as pbar:
            for future in as_completed(futures):
                _ = future.result()
                pbar.update(1)
