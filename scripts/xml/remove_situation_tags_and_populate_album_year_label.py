"""This module is a script for modifying a Collection.

More specifically, it queries Spotify for each track and attempts to resolve
the year, album, and label. In addition, it removes "situation" tags
{"Opener", "Build", "Peak Time"} from the Comments field. This is done because
I'm now re-purposing the "Rating" field to convey the energy level of tracks.
"""
from argparse import ArgumentParser
from concurrent.futures import as_completed, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import re

from tqdm import tqdm

from djtools.configs.helpers import build_config
from djtools.collection.collections import RekordboxCollection
from djtools.spotify.helpers import filter_results, get_spotify_client


def thread(track):
    """Threaded function.

    Hits the Spotify API and tries to find a matching track. If found, resolve
    the year, album, and label fields of the track. Then, if the track has
    "My Tag" data in the Comments field, remove the "situation" tags.

    Args:
        track: A Track object.
    """
    # Search Spotify for the track.
    title = getattr(track, "_Name")
    artist = getattr(track, "_Artist")
    query = f"track:{title} artist:{artist}"
    results = spotify.search(q=query, type="track", limit=50)
    match, _ = filter_results(spotify, results, threshold, title, artist)
    if match:
        result = spotify.album(match["album"]["id"])
        album = result["name"]
        label = result["label"]
        for date_format in ["%Y-%m-%d", "%Y-%m", "%Y"]:
            try:
                date = datetime.strptime(result["release_date"], date_format)
            except ValueError:
                continue
        year = str(date.year)
        for attribute_name, attribute in [
            ("album", album),
            ("label", label),
            ("year", year),
        ]:
            setattr(track, f"_{attribute_name.title()}", attribute)

    # Remove "Situation" tags.
    comments = getattr(track, "_Comments")
    tags = re.search(tag_regex, comments)
    if not tags:
        return
    comment_prefix = comments.split("/* ")[0].strip()
    comment_suffix = comments.split(" */")[-1].strip()
    new_tags = [
        tag.strip()
        for tag in tags.group().split("/")
        if tag.strip() not in remove_tags
    ]
    new_tags = " / ".join(new_tags)
    if new_tags:
        setattr(
            track,
            "_Comments",
            f"{comment_prefix} /* {new_tags} */ {comment_suffix}",
        )
    else:
        setattr(track, "_Comments", f"{comment_prefix} {comment_suffix}")


if __name__ == "__main__":
    arg_parser = ArgumentParser()
    arg_parser.add_argument("--config", help="Path to a config.yaml")
    arg_parser.add_argument("--collection", help="Path to a collection")
    args = arg_parser.parse_args()
    config_path = Path(args.config)
    collection = RekordboxCollection(path=Path(args.collection))
    config = build_config(config_path)
    spotify = get_spotify_client(config)
    threshold = config.SPOTIFY_PLAYLIST_FUZZ_RATIO
    tag_regex = re.compile(r"(?<=\/\*).*(?=\*\/)")
    remove_tags = {"Opener", "Build", "Peak Time"}
    tracks = collection.get_tracks().values()
    with tqdm(total=len(tracks)) as pbar:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(thread, track) for track in tracks]
            for future in as_completed(futures):
                future.result()
                pbar.update(1)
    collection.serialize(config_path.parent / f"auto_{config_path.name}")
