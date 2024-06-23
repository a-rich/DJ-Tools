"""This is a script for moving tag data around for consistent formatting.

Supported functions include:

* moving particular tags from the `Comments` field to the `Genre` field
* moving particular tags from in the `Comments` field to the front of that field
"""

from argparse import ArgumentParser
from pathlib import Path
import re
from typing import Any, Dict, Set

import bs4
from bs4 import BeautifulSoup


def parse_args() -> Dict[str, Any]:
    """Parses command-line arguments.

    Returns:
        Dictionary of arguments.
    """

    def parse_path(path):
        try:
            path = Path(path)
            if not path.exists():
                raise FileNotFoundError(f"{path} does not exist.")
        except Exception as exc:
            raise TypeError(f"{path} is not a valid path.") from exc
        return path

    parser = ArgumentParser()
    parser.add_argument(
        "--mode",
        "-m",
        type=str,
        choices=[
            "move-genres-from-comments",
            "move-tags-to-front-of-comments",
        ],
        required=True,
        help="Path to Rekordbox XML file.",
    )
    parser.add_argument(
        "--xml",
        "-x",
        type=parse_path,
        required=True,
        help="Path to Rekordbox XML file.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="output_rekordbox.xml",
        help="Path to output Rekordbox XML file.",
    )
    parser.add_argument(
        "--tags",
        "-t",
        type=str,
        nargs="+",
        required=True,
        help='List of "My Tags" to be relocated.',
    )
    parser.add_argument(
        "--tag_delimiter",
        "-g",
        type=str,
        default="/",
        help="Character used to separate tags.",
    )

    return vars(parser.parse_args())


def move_genres_from_comments(
    track: bs4.element.Tag,
    my_tags: Set[str],
    tags: Set[str],
    tag_delimiter: str,
) -> bs4.element.Tag:
    """Moves `tags` from `my_tags` to the `Genre` field.

    Args:
        track: Track node.
        my_tags: Tags extracted from the `Comments` field.
        tags: Tags targeted for relocation.
        tag_delimiter: Delimiter used to separate tags within a field.

    Returns:
        Updated track node.
    """
    # Filter "My Tags" for tags belonging to the provided set of tags
    # to be relocated.
    new_genre_tags = []
    new_comments_tags = []
    for tag in my_tags.group().split("/"):
        tag = tag.strip()
        if not tag in tags:
            new_comments_tags.append(tag)
            continue
        new_genre_tags.append(tag)
    if not new_genre_tags:
        return track
    # Get pre-existing tags and split them on the chosen delimiter.
    current_tags = [x.strip() for x in track["Genre"].split(tag_delimiter)]
    # Deduplicate tags across pre-existing tags and "My Tags".
    if current_tags:
        new_genre_tags = set(current_tags).union(set(new_genre_tags))
    # Write new tags to field.
    track["Genre"] = f" {tag_delimiter} ".join(new_genre_tags)
    track["Comments"] = " / ".join(new_comments_tags)

    return track


def move_tags_to_front_of_comments(
    track: bs4.element.Tag,
    my_tags: Set[str],
    tags: Set[str],
    **kwargs,  # pylint: disable=unused-argument
) -> bs4.element.Tag:
    """Moves `tags` from `my_tags` to the front of the `Comments` field.

    Args:
        track: Track node.
        my_tags: Tags extracted from the `Comments` field.
        tags: Tags targeted for relocation.

    Returns:
        Updated track node.
    """
    tags_to_move = []
    remainder_tags = []
    for tag in my_tags.group().split("/"):
        tag = tag.strip()
        if tag in tags:
            tags_to_move.append(tag)
        else:
            remainder_tags.append(tag)
    if not tags_to_move:
        return track
    if len(tags_to_move) > 1:
        print(f"{track['Name']} has more than 1 situation tag: {tags_to_move}")
    comment_prefix = track["Comments"].split("/* ")[0]
    comment_suffix = track["Comments"].split(" */")[-1]
    new_my_tags = " / ".join(tags_to_move + remainder_tags)
    # Write new tags to Comments field.
    track["Comments"] = f"{comment_prefix} /* {new_my_tags} */{comment_suffix}"

    return track


move_functions = {
    "move-genres-from-comments": move_genres_from_comments,
    "move-tags-to-front-of-comments": move_tags_to_front_of_comments,
}


def move_tags(
    mode: str,
    xml: str,
    tags: Set[str],
    output: str,
    tag_delimiter: str,
):
    """Moved data from the `Comments` field.

    Behavior depends on the `mode` argument.

    The provided XML must be an valid XML export:
        `File > Export Collection in xml format`

    The provided tags must match exactly the data written to the Comments field
    (case-sensitive).

    The provided output must be the path to a XML file from which you'll import
    the adjusted data.

    Comments field tags are expected to have the format `/* tag1 / tag2 */`
    which is the way Rekordbox's "My Tag" system writes the data to the
    Comments field.

    Rekordbox's "My Tag" system will write data to the Comments field only if
    the following setting is enabled:
        `Preferences > Advanced > Browse > Add "My Tag" to the "Comments"`

    Args:
        xml: Path to a Rekordbox XML file.
        tags: Set of "My Tags" to be relocated.
        output: Path to an output Rekordbox XML file.
        tag_delimiter: Character used to delimit field tags.

    Raises:
        RuntimeError: `xml` must be a valid XML file.
    """
    try:
        with open(xml, mode="r", encoding="utf-8") as _file:
            database = BeautifulSoup(_file.read(), "xml")
    except Exception as exc:
        raise RuntimeError(
            "Are you sure the provided XML is valid? Parsing it failed with "
            f"the following exception:\n{exc}"
        ) from exc

    # Regular expression to isolate "My Tags".
    my_tag_regex = re.compile(r"(?<=\/\*).*(?=\*\/)")

    for track in database.find_all("TRACK"):
        # Make sure this isn't a TRACK node for a playlist.
        if not track.get("Location"):
            continue
        # Get "My Tags", if any, from the Comments field.
        my_tags = re.search(my_tag_regex, track["Comments"])
        if not my_tags:
            continue
        track = move_functions[mode](
            track=track,
            my_tags=my_tags,
            tags=tags,
            tag_delimiter=tag_delimiter,
        )

    # Write output rekordbox.xml to file.
    with open(output, mode="wb", encoding=database.original_encoding) as _file:
        _file.write(database.prettify("utf-8"))


if __name__ == "__main__":
    parsed_args = parse_args()
    if not parsed_args["tags"]:
        raise RuntimeError(
            'The --tags option must include a list of "My Tag" to be relocated'
        )
    parsed_args["tags"] = set(parsed_args["tags"])
    move_tags(**parsed_args)
