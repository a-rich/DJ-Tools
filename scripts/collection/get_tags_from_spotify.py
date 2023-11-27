"""This module is a script for modifying a Collection.

More specifically, it queries Spotify for each track and attempts to resolve
the year, album, and label.
"""
from argparse import ArgumentParser
from concurrent.futures import as_completed, ThreadPoolExecutor
from datetime import datetime
import os
from pathlib import Path

from tqdm import tqdm

from djtools.configs.helpers import build_config
from djtools.collection.helpers import PLATFORM_REGISTRY
from djtools.spotify.helpers import filter_results, get_spotify_client


def get_spotify_tags_thread(track, spotify, threshold):
    """Threaded function.

    Hits the Spotify API and tries to find a matching track. If found, resolve
    the year, album, and label fields of the track.

    Args:
        track: A Track object.
        spotify: Spotify client.
        threshold: Minimum Spotify result similarity for a match.
    """
    title = getattr(track, "_Name")
    artist = track.get_artists()
    results = spotify.search(
        q=f"track:{title} artist:{artist}", type="track", limit=50
    )
    result, _ = filter_results(spotify, results, threshold, title, artist)
    if result:
        album = spotify.album(result["album"]["id"])
        for date_format in ["%Y-%m-%d", "%Y-%m", "%Y"]:
            try:
                date = datetime.strptime(album["release_date"], date_format)
            except ValueError:
                continue
        for attribute_name, attribute in [
            ("album", album["name"]),
            ("label", album["label"]),
            ("year", str(date.year)),
        ]:
            setattr(track, f"_{attribute_name.title()}", attribute)


if __name__ == "__main__":
    arg_parser = ArgumentParser()
    arg_parser.add_argument("--config", help="Path to a config.yaml")
    arg_parser.add_argument(
        "--output_collection", help="Path to output collection"
    )
    args = arg_parser.parse_args()

    # Build config, instantiate collection, and get tracks.
    config_path = Path(args.config)
    config = build_config(config_path)
    collection = PLATFORM_REGISTRY[config.PLATFORM]["collection"](
        path=config.COLLECTION_PATH
    )
    tracks = collection.get_tracks().values()

    # Add tags from Spotify.
    spotify = get_spotify_client(config)
    threshold = config.SPOTIFY_PLAYLIST_FUZZ_RATIO
    with tqdm(
        total=len(tracks), desc="Adding tags from Spotify"
    ) as pbar, ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as pool:
        futures = [
            pool.submit(get_spotify_tags_thread, track, spotify, threshold)
            for track in tracks
        ]
        for future in as_completed(futures):
            future.result()
            pbar.update(1)

    playlist_class = PLATFORM_REGISTRY[config.PLATFORM]["playlist"]
    playlist = playlist_class.new_playlist(
        name=args.playlist_name, tracks=tracks
    )
    collection.add_playlist(playlist)
    output = args.output_collection if args.output_collection else config_path
    collection.serialize(output)
