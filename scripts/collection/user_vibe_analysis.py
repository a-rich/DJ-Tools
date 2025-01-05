"""This script is used to generate histograms of My Tags per user."""

# pylint: disable=import-error,redefined-outer-name,unused-argument,invalid-name
from argparse import ArgumentParser
from collections import defaultdict
from itertools import groupby
from pathlib import Path
from typing import Optional, Set

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from djtools.configs import build_config
from djtools.collection.base_collection import Collection
from djtools.collection.platform_registry import PLATFORM_REGISTRY


def analyze_collection_vibes(
    collection: Collection,
    included_tags: Optional[Set] = None,
    **kwargs,
):
    """Create histograms that show a collection's distribution of My Tags.

    Args:
        collection: Collection object.
        included_tags: My Tags to include in the histograms.
    """
    tracks = collection.get_tracks().values()
    tag_counts = {tag: 0 for tag in included_tags}
    for track in tracks:
        tags = set(track.get_tags()).difference(track.get_genre_tags())
        for tag in tags:
            if tag not in tag_counts:
                continue
            tag_counts[tag] += 1

    fig, ax = plt.subplots()
    fig.suptitle("Collection Vibes", fontsize=16, fontweight="extra bold")
    fig.text(0.5, 0.04, "Vibes", fontsize=16, ha="center", fontweight="bold")
    fig.text(
        0.04,
        0.5,
        "Number of Tags",
        fontsize=16,
        va="center",
        rotation="vertical",
        fontweight="bold",
    )
    x_ticks = list(range(len(tag_counts)))
    ax.bar(x_ticks, list(tag_counts.values()))
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(list(tag_counts.keys()), rotation=70, fontsize=14)
    plt.tight_layout()
    plt.show()


def analyze_user_vibes(
    collection: Collection,
    user_index: int,
    included_tags: Optional[Set] = None,
    verbosity: int = 0,
    **kwargs,
):
    """Create histograms that show each user's distribution of My Tags.

    Args:
        collection: Collection object.
        user_index: Part of the `Location` path the corresponds to a username.
        included_tags: My Tags to include in the histograms.
        verbosity: Verbosity level.
    """
    tracks = collection.get_tracks().values()

    # Collect user-tag data.
    included_tags = included_tags or set()
    user_tags = defaultdict(lambda: defaultdict(int))
    for user, tracks in groupby(
        sorted(tracks, key=lambda x: x.get_location()),
        key=lambda x: list(filter(None, str(x.get_location()).split("/")))[
            user_index
        ],
    ):
        tagged_tracks = 0
        tracks = list(tracks)
        for track in tracks:
            tags = (
                set(track.get_tags())
                .difference(track.get_genre_tags())
                .intersection(included_tags)
            )
            if not tags:
                continue
            tagged_tracks += 1
            for tag in tags:
                user_tags[user][tag] += 1
        if verbosity:
            print(
                f"{user}\n\tTracks: {len(tracks)}\n\tTagged tracks: "
                f"{tagged_tracks}\n\tTags: {sum(user_tags[user].values())}"
            )

    # Plot bar charts for each user.
    rows = len(user_tags) // 2
    fig, ax = plt.subplots(rows, 2)  # pylint: disable=invalid-name
    fig.suptitle("User Vibes", fontsize=16, fontweight="extra bold")
    fig.text(0.5, 0.04, "Vibes", fontsize=16, ha="center", fontweight="bold")
    fig.text(
        0.04,
        0.5,
        "Number of Tags",
        fontsize=16,
        va="center",
        rotation="vertical",
        fontweight="bold",
    )
    # included_tags = sorted(
    #     set(key for tag in user_tags.values() for key in tag.keys())
    # )
    x_ticks = list(range(len(included_tags)))
    for idx, (user, tags) in enumerate(user_tags.items()):
        tags.update({vibe: 0 for vibe in included_tags if vibe not in tags})
        ax[idx % 2, int(idx < rows)].bar(
            x_ticks, [tags[vibe] for vibe in included_tags]
        )
        ax[idx % 2, int(idx < rows)].set_title(f"{user}", fontsize=14)
        ax[idx % 2, int(idx < rows)].set_xticks(x_ticks)
        ax[idx % 2, int(idx < rows)].yaxis.set_major_locator(
            MaxNLocator(integer=True)
        )
        if idx % 2 == rows - 1:
            ax[idx % 2, int(idx < rows)].set_xticklabels(
                included_tags, rotation=70, fontsize=14
            )
        else:
            ax[idx % 2, int(idx < rows)].set_xticklabels([])
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--collection",
        type=str,
        required=False,
        help="Path to collection.",
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to config.yaml.",
    )
    parser.add_argument(
        "--included-tags",
        nargs="+",
        default=[
            "Aggro",
            "Heavy",
            "Rave",
            "Gangsta",
            "Bounce",
            "Groovy",
            "Deep",
            "Atmospheric",
            "Hypnotic",
            "Dark",
            "Melancholy",
            "Melodic",
            "Uplifting",
            "Strange",
        ],
        help="Included tags",
    )
    parser.add_argument(
        "--mode",
        choices=["collection", "user"],
        default="collection",
        help="Whether to analyze vibes across the whole collection or on a per-user level.",
    )
    parser.add_argument(
        "--user-index",
        type=int,
        default=3,
        help="Index of path part corresponding to username",
    )
    parser.add_argument(  # pylint: disable=duplicate-code
        "--verbosity",
        "-v",
        action="count",
        default=0,
        help="verbosity",
    )
    args = parser.parse_args()

    # Load config and, if provided, override path to collection.
    config_path = Path(args.config)
    config = build_config(config_path)

    # Load collection and get a dict of tracks keyed by location.
    collection = PLATFORM_REGISTRY[config.platform]["collection"](
        path=args.collection or config.collection_path
    )
    args.collection = collection

    if args.mode == "collection":
        analyze_collection_vibes(**vars(args))
    elif args.mode == "user":
        analyze_user_vibes(**vars(args))
