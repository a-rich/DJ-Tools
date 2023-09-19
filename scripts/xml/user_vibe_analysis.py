"""This script is used to generate histograms of My Tags per user."""
from argparse import ArgumentParser
from collections import defaultdict
from itertools import groupby
import re
from typing import Optional, Set

from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


def analyze_user_vibes(
    xml: str,
    user_index: int,
    excluded_tags: Optional[Set] = None,
    verbosity: int = 0,
):
    """Create histograms that show each user's distribution of My Tags.

    Args:
        xml: Path to a Rekordbox XML file.
        user_index: Part of the `Location` path the corresponds to a username.
        excluded_tags: My Tags to exclude from the histograms.
        verbosity: Verbosity level.
    """
    # Read tracks from XML.
    with open(xml, mode="r", encoding="utf-8") as _file:
        soup = BeautifulSoup(_file.read(), "xml")
        tracks = [
            track for track in soup.find_all("TRACK") if track.get("Location")
        ]

    # Collect user-tag data.
    excluded_tags = excluded_tags or set()
    regex = re.compile(r"(?<=\/\*).*(?=\*\/)")
    user_tags = defaultdict(lambda: defaultdict(int))
    for user, tracks in groupby(
        sorted(tracks, key=lambda x: x["Location"]),
        key=lambda x: x["Location"].split("/")[user_index],
    ):
        tagged_tracks = 0
        tracks = list(tracks)
        for track in tracks:
            tags = re.search(regex, track.get("Comments"))
            if not tags:
                continue
            tagged_tracks += 1
            tags = {x.strip() for x in tags.group().split("/")}.difference(
                excluded_tags
            )
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
    vibes = sorted(
        set(key for tag in user_tags.values() for key in tag.keys())
    )
    x_ticks = list(range(len(vibes)))
    for idx, (user, tags) in enumerate(user_tags.items()):
        tags.update({vibe: 0 for vibe in vibes if vibe not in tags})
        ax[idx % 2, int(idx < rows)].bar(
            x_ticks, [tags[vibe] for vibe in vibes]
        )
        ax[idx % 2, int(idx < rows)].set_title(f"{user}", fontsize=14)
        ax[idx % 2, int(idx < rows)].set_xticks(x_ticks)
        ax[idx % 2, int(idx < rows)].yaxis.set_major_locator(
            MaxNLocator(integer=True)
        )
        if idx % 2 == rows - 1:
            ax[idx % 2, int(idx < rows)].set_xticklabels(
                vibes, rotation=70, fontsize=14
            )
        else:
            ax[idx % 2, int(idx < rows)].set_xticklabels([])
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--xml",
        type=str,
        required=True,
        help="Path to rekordbox.xml",
    )
    parser.add_argument(
        "--user-index",
        type=int,
        default=6,
        help="Index of path part corresponding to username",
    )
    parser.add_argument(
        "--excluded-tags",
        nargs="+",
        default=[
            "Opener",
            "Build",
            "Peak Time",
            "Flute",
            "Guitar",
            "Piano",
            "Vocal",
        ],
        help="Excluded tags",
    )
    parser.add_argument(  # pylint: disable=duplicate-code
        "--verbosity",
        "-v",
        action="count",
        default=0,
        help="verbosity",
    )
    analyze_user_vibes(**vars(parser.parse_args()))
