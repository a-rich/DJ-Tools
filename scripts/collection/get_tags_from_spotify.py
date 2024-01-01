"""This module is a script for modifying a Collection.

More specifically, it queries Spotify for each track and attempts to resolve
the year, album, and label.
"""
# pylint: disable=redefined-outer-name,duplicate-code
from argparse import ArgumentParser
from concurrent.futures import as_completed, ThreadPoolExecutor
from datetime import datetime
import os

from tqdm import tqdm

from djtools.configs.helpers import build_config
from djtools.collection.helpers import PLATFORM_REGISTRY
from djtools.spotify.helpers import filter_results, get_spotify_client


def get_spotify_tags_thread(track, spotify, threshold, query_limit):
    """Threaded function.

    Hits the Spotify API and tries to find a matching track. If found, resolve
    the year, album, and label fields of the track.

    Args:
        track: A Track object.
        spotify: Spotify client.
        threshold: Minimum Spotify result similarity for a match.
        query_limit: Number of Spotify query results.
    """
    title = getattr(track, "_Name")
    artist = track.get_artists()
    results = spotify.search(
        q=f"track:{title} artist:{artist}", type="track", limit=query_limit
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
    arg_parser.add_argument("--collection", help="Path to a collection.")
    arg_parser.add_argument("--config", help="Path to a config.yaml.")
    arg_parser.add_argument(
        "--mode",
        choices=["bulk", "interactive"],
        default="interactive",
        help="Bulk process tracks or review individual tracks.",
    )
    arg_parser.add_argument("--output", help="Path to output collection.")
    arg_parser.add_argument(
        "--query-limit",
        type=int,
        default=50,
        help="Number of Spotify query results.",
    )
    arg_parser.add_argument(
        "--similarity",
        type=int,
        default=90,
        help="Minimum Levenshtein distance for a Spotify query result to match a track.",
    )
    args = arg_parser.parse_args()

    # Build config, instantiate collection, and get tracks.
    config = build_config(args.config)
    collection = PLATFORM_REGISTRY[config.PLATFORM]["collection"](
        path=args.collection or config.COLLECTION_PATH
    )
    tracks = collection.get_tracks()
    spotify = get_spotify_client(config)
    playlist_class = PLATFORM_REGISTRY[config.PLATFORM]["playlist"]

    # Add tags from Spotify.
    if args.mode == "bulk":
        with tqdm(
            total=len(tracks), desc="Adding tags from Spotify"
        ) as pbar, ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as pool:
            futures = [
                pool.submit(
                    get_spotify_tags_thread, track, spotify, args.similarity
                )
                for track in tracks
            ]
            for future in as_completed(futures):
                future.result()
                pbar.update(1)

        playlist = playlist_class.new_playlist(
            name=args.playlist_name, tracks=tracks
        )
        collection.add_playlist(playlist)
    elif args.mode == "interactive":
        no_matches = {}
        same_tracks = {}
        updated_tracks = {}

        for track_id, track in tqdm(tracks.items()):
            # Query Spotify for matching tracks
            title = track._Name
            artist = track.get_artists()
            query = f"track:{title} artist:{artist}"
            results = spotify.search(
                q=query, type="track", limit=args.query_limit
            )

            # Get result most similar to query.
            result, _ = filter_results(
                spotify, results, args.similarity, title, artist
            )

            # Mark track as a non-match and continue.
            if not result:
                no_matches[track_id] = track
                continue

            # Query album for the track.
            album = spotify.album(result["album"]["id"])
            for date_format in ["%Y-%m-%d", "%Y-%m", "%Y"]:
                try:
                    date = datetime.strptime(
                        album["release_date"], date_format
                    )
                except ValueError:
                    continue

            # Display comparison of track data from Collection vs. Spotify.
            artists = ", ".join([x["name"] for x in result["artists"]])
            print(
                f"C: {title} - {artist}: "
                f"{track._Album}, {track._Label}, {track._Year}\n"
                f"S: {result['name']} - {artists}: "
                f"{album['name']}, {album['label']}, {str(date.year)}"
            )

            # Check input for signal to skip or accept new tags.
            next = False
            while not next:
                resp = input("[y] accept, [n] skip")
                if "n" in resp:
                    same_tracks[track_id] = track
                    next = True
                elif "y" in resp:
                    for attribute_name, attribute in [
                        ("album", album["name"]),
                        ("label", album["label"]),
                        ("year", str(date.year)),
                    ]:
                        setattr(track, f"_{attribute_name.title()}", attribute)
                        updated_tracks[track_id] = track
                    next = True
                else:
                    print(
                        "Response must contain either 'n' or 'y' -- try again!"
                    )

        playlist_class = PLATFORM_REGISTRY[config.PLATFORM]["playlist"]
        for name, set_tracks in [
            ("No matches", no_matches),
            ("Same", same_tracks),
            ("Updated", updated_tracks),
        ]:
            playlist = playlist_class.new_playlist(
                name=name, tracks=set_tracks
            )
            collection.add_playlist(playlist)

    collection.serialize(path=args.output or config.COLLECTION_PATH)
