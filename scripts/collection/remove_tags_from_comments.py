"""This module is a script for modifying a Collection.

More specifically, it queries Spotify for each track and attempts to resolve
the year, album, and label. In addition, it removes "situation" tags
{"Opener", "Build", "Peak Time"} from the Comments field. This is done because
I'm now re-purposing the "Rating" field to convey the energy level of tracks.
"""

# pylint: disable=redefined-outer-name,duplicate-code
from argparse import ArgumentParser
from concurrent.futures import as_completed, ThreadPoolExecutor
import os
from pathlib import Path
import re
import sys

from tqdm import tqdm

from djtools.configs.helpers import build_config
from djtools.collection.platform_registry import PLATFORM_REGISTRY


def remove_tags_thread(track, tag_regex, remove_tags):
    """Threaded function.

    If the track has "My Tag" data in the Comments field, remove the
    provided tags.

    Args:
        track: A Track object.
        tag_regex: Regular expression to match tags in the comments.
        remove_tags: List of tags to exclude from the comments.
    """
    field = getattr(track, "_Comments")
    tags = re.search(tag_regex, field)
    if not tags:
        return
    comment_prefix = field.split("/* ")[0].strip()
    comment_suffix = field.split(" */")[-1].strip()
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
    arg_parser.add_argument(
        "--output_collection", help="Path to output collection"
    )
    arg_parser.add_argument(
        "--remove-tags", nargs="+", help="List of tags to remove"
    )
    args = arg_parser.parse_args()

    # Build config, instantiate collection, and get tracks.
    config_path = Path(args.config)
    config = build_config(config_path)
    collection = PLATFORM_REGISTRY[config.platform]["collection"](
        path=config.collection_path
    )
    tracks = collection.get_tracks().values()

    if not args.remove_tags:
        sys.exit("You must provide --remove-tags!")

    # Remove tags from a particular field.
    tag_regex = re.compile(r"(?<=\/\*).*(?=\*\/)")
    remove_tags = set(args.remove_tags)
    with (
        tqdm(
            total=len(tracks),
            desc=f"Removing tags from {args.remove_tags_fields}",
        ) as pbar,
        ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as pool,
    ):
        futures = [
            pool.submit(remove_tags_thread, track, tag_regex, remove_tags)
            for track in tracks
        ]
        for future in as_completed(futures):
            future.result()
            pbar.update(1)

    playlist_class = PLATFORM_REGISTRY[config.platform]["playlist"]
    playlist = playlist_class.new_playlist(
        name=args.playlist_name, tracks=tracks
    )
    collection.add_playlist(playlist)
    output = args.output_collection if args.output_collection else config_path
    collection.serialize(output)
