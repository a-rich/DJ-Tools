"""This module is a script for normalizing the audio to have a peak amplitude
of 0.0 decibels.
"""

# pylint: disable=import-error
from argparse import ArgumentParser
from collections import defaultdict
from concurrent.futures import as_completed, ThreadPoolExecutor
import json
from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
from pydub import AudioSegment, effects, utils
from tqdm import tqdm

from djtools.collection.rekordbox_collection import RekordboxCollection
from djtools.collection.rekordbox_track import RekordboxTrack


def thread(track: RekordboxTrack, data_dict: Dict):
    """Normalize the amplitude of tracks to have 0.0 headroom.

    Overwrite the track's audio file with the normalized audio. Tags are
    retained and audio files are exported at 320 kbps. Collect the dB
    frequencies and filenames for analysis.

    Args:
        track: Track object.
        data_dict: Dictionary mapping amplitude to a frequency count and list
            of tracks.
    """
    loc = track.get_location()
    audio = AudioSegment.from_file(loc)
    if audio.max_dBFS < 0.0:
        audio = effects.normalize(audio, headroom=0.0)
        audio.export(
            loc,
            tags=utils.mediainfo(loc).get("TAG", {}),
            bitrate="320k",
        )
    # Round off these values now or else aggregate keys in the dB_data.json
    # file written at the end of this script.
    # NOTE: your bar chart will probably be hard to read unless you aggregate
    # these keys.
    data_dict[audio.max_dBFS]["count"] += 1
    data_dict[audio.max_dBFS]["tracks"].append(loc.name)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--collection", help="Path to collection")
    args = parser.parse_args()

    # Submit normalization jobs to a thread pool and collect dB data.
    collection = RekordboxCollection(Path(args.collection))
    tracks = collection.get_tracks().values()
    data = defaultdict(lambda: {"count": 0, "tracks": []})
    with tqdm(total=len(tracks)) as pbar:
        with ThreadPoolExecutor(max_workers=32) as pool:
            futures = [pool.submit(thread, track, data) for track in tracks]
            for future in as_completed(futures):
                future.result()
                pbar.update()

    # Write collected data to a JSON file.
    with open("dB_data.json", mode="w", encoding="UTF-8") as _file:
        json.dump(data, _file)

    # Plot log scale amplitudes.
    data = {k: data[k] for k in sorted(data)}
    plt.figure(figsize=(10, 6))
    plt.bar(list(data.keys()), [v["count"] for v in data.values()])
    plt.title("Collection Peak Amplitudes (log scale)", fontweight="bold")
    plt.xlabel("Amplitude", fontweight="bold")
    plt.ylabel("Frequency", fontweight="bold")
    plt.yscale("log")
    plt.tick_params(left=False, bottom=False)
    plt.tight_layout()
    plt.savefig("Collection Peak Amplitudes")
