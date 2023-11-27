"""This is a script for sorting the non-genre tags of a collection in
alphabetical order.
"""
from argparse import ArgumentParser
from pathlib import Path

from djtools.configs import build_config
from djtools.collection.helpers import PLATFORM_REGISTRY


TAG_ORDERINGS = (
    (
        "Aggro",
        "Atmospheric",
        "Bounce",
        "Dark",
        "Deep",
        "Gangsta",
        "Groovy",
        "Heavy",
        "Hypnotic",
        "Melancholy",
        "Melodic",
        "Rave",
        "Strange",
        "Uplifting",
    ),
    ("Flute", "Guitar", "Horn", "Piano", "Strings", "Vocal"),
    ("Loop", "Scratch"),
)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--config", required=True, help="Path to a config.yaml"
    )
    parser.add_argument(
        "--collection", required=False, help="Path to a collection"
    )
    args = parser.parse_args()

    # Load config and, if provided, override path to collection.
    config = build_config(args.config)
    if args.collection:
        config.COLLECTION_PATH = Path(args.collection)

    # Load collection and get a dict of tracks keyed by location.
    collection = PLATFORM_REGISTRY[config.PLATFORM]["collection"](
        path=config.COLLECTION_PATH
    )

    tracks = collection.get_tracks()
    tag_sets = [set(tags) for tags in TAG_ORDERINGS]
    affected = not_affected = 0

    for track in tracks.values():
        all_tags = track.get_tags()
        genre_tags = set(track.get_genre_tags())
        track_tag_set = set(all_tags).difference(genre_tags)
        new_tags = []
        for tag_order, tag_set in zip(TAG_ORDERINGS, tag_sets):
            new_tags.extend(
                sorted([tag for tag in track_tag_set.intersection(tag_set)])
            )
        tags_before = [tag for tag in all_tags if tag not in genre_tags]
        if tags_before != new_tags:
            affected += 1
            print(f"{tags_before}\n{new_tags}\n")
            # track._Tags = new_tags
        else:
            not_affected += 1

    # collection.serialize()

    print(f"affected: {affected}")
    print(f"not affected: {not_affected}")
