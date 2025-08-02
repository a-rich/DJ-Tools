"""This is a script for sorting the non-genre tags of a collection in
alphabetical order.
"""

# pylint: disable=protected-access
from argparse import ArgumentParser
import re

from djtools.configs import build_config
from djtools.collection.platform_registry import PLATFORM_REGISTRY


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
    ("DELETE",),
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

    # Load config and collection and get a dict of tracks keyed by location.
    config = build_config(args.config)
    collection = PLATFORM_REGISTRY[config.platform]["collection"](
        path=args.collection or config.collection_path
    )
    playlist_class = PLATFORM_REGISTRY[config.platform]["playlist"]

    tracks = collection.get_tracks()
    tag_sets = [set(tags) for tags in TAG_ORDERINGS]
    MY_TAGS_REGEX = r"(?<=\/\*).*(?=\*\/)"
    affected_tracks = {}

    for track_id, track in tracks.items():
        all_tags = track.get_tags()
        genre_tags = set(track.get_genre_tags())
        track_tag_set = set(all_tags).difference(genre_tags)
        new_tags = []
        for tag_order, tag_set in zip(TAG_ORDERINGS, tag_sets):
            new_tags.extend(sorted(track_tag_set.intersection(tag_set)))

        tags_before = [tag for tag in all_tags if tag not in genre_tags]
        if tags_before != new_tags:
            print(
                f"{track._Name} - {track._Artist}\n{tags_before}\n{new_tags}\n"
            )
            track._Comments = re.sub(
                MY_TAGS_REGEX,
                " " + " / ".join(new_tags) + " ",
                track._Comments,
            )
            affected_tracks[track_id] = track

    collection.add_playlist(
        playlist_class.new_playlist(
            name="Tracks with sorted comments", tracks=affected_tracks
        )
    )
    collection.serialize()

    print(f"{len(affected_tracks)} out of {len(tracks)} tracks were affected.")
