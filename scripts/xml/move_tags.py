from argparse import ArgumentParser
from pathlib import Path
import re
from typing import Any, Dict, Set

import bs4
from bs4 import BeautifulSoup, 


def parse_args() -> Dict[str, Any]:
    """Parses command-line arguments.

    Returns:
        Dictionary of arguments.
    """

    def parse_path(x):
        try:
            x = Path(x)
            if not x.exists():
                raise FileNotFoundError(f"{x} does not exist.")
        except Exception:
            raise TypeError(f"{x} is not a valid path.")
        return x

    parser = ArgumentParser()
    parser.add_argument(
        "--mode",
        "-m",
        type=str,
        choices=[
            "move_genres_from_comments", "move_tags_to_front_of_comments"
        ],
        default="move_tags_to_front_of_comments",
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
    args = parser.parse_args()

    return vars(args)


def move_genres_from_comments(
    track: bs4.elment.Tag,
    my_tags: Set[str],
    tag_delimiter: str,
    tags: Set[str],
    *args,
    **kwargs,
) -> bs4.element.Tag:
    # Filter "My Tags" for tags belonging to the provided set of tags
    # to be relocated.
    new_tags = [
        x.strip() for x in my_tags.group().split("/") if x.strip() in tags
    ]
    if not new_tags:
        return track
    # Get pre-existing tags and split them on the chosen delimiter.
    current_tags = [
        x.strip() for x in track["Genre"].split(tag_delimiter)
    ]
    # Deduplicate tags across pre-existing tags and "My Tags".
    if current_tags:
        new_tags = set(current_tags).union(set(new_tags))
    # Write new tags to field.
    track["Genre"] = f" {tag_delimiter} ".join(new_tags)

    return track


def move_tags_to_front_of_comments(
    track: bs4.elment.Tag,
    my_tags: Set[str],
    tags: Set[str],
    *args,
    **kwargs,
) -> bs4.element.Tag:
    # Filter "My Tags" for tags to be moved to the front of the field. 
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
    new_my_tags = f" / ".join(tags_to_move + remainder_tags)
    # Write new tags to Comments field.
    track["Comments"] = (
        f"{comment_prefix} /* {new_my_tags} */{comment_suffix}"
    )

    return track


move_functions = {
    "move_genres_from_comments": move_genres_from_comments,
    "move_tags_to_front_of_comments": move_tags_to_front_of_comments,
}


def move_tags(
    mode: str,
    xml: str,
    tags: Set[str],
    output: str,
    tag_delimiter: str,
):
    """Copies selected tags from the Comments field to the Genre field.

    The provided XML must be an valid XML export:
        `File > Export Collection in xml format`
    
    The provided tags must match exactly the data written to the Comments field
    (case-sensative). 

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
        FileNotFoundError: `xml` must be a file that exists.
        Exception: `xml` must be a valid XML file.
    """
    try:
        with open(xml, mode="r", encoding="utf-8") as _file:
            db = BeautifulSoup(_file.read(), "xml")
    except Exception as exc:
        raise Exception(
            "Are you sure the provided XML is valid? Parsing it failed with "
            f"the following exception:\n{exc}"
        )
    
    # Regular expression to isolate "My Tags".
    my_tag_regex = re.compile(r"(?<=\/\*).*(?=\*\/)")

    for track in db.find_all("TRACK"):
        # Make sure this isn't a TRACK node for a playlist.
        if not track.get("Location"):
            continue
        # Get "My Tags", if any, from the Comments field.
        my_tags = re.search(my_tag_regex, track["Comments"])
        if not my_tags:
            continue
        track = move_functions[mode](track, my_tags, tags, tag_delimiter)

    # Write output rekordbox.xml to file.
    with open(output, mode="wb", encoding=db.orignal_encoding) as _file:
        _file.write(db.prettify("utf-8"))


if __name__ == "__main__":
    """Move the provided "My Tags".

    Raises:
        RuntimeError: the --tags option must contain one or more "My Tags" to
            relocated.
    """
    args = parse_args()
    if not args["tags"]:
        raise RuntimeError(
            'The --tags option must include a list of "My Tag" to be relocated'
        )
    args["tags"] = set(args["tags"])
    move_tags(
        mode=args["mode"],
        xml=args["xml"],
        tags=args["tags"],
        output=args["output"],
        tag_delimiter=args["tag_delimiter"],
    )
