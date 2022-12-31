from argparse import ArgumentParser
import re
import os
from typing import Any, Dict, Set

from bs4 import BeautifulSoup


def parse_args() -> Dict[str, Any]:
    """Parses command-line arguments.

    Returns:
        Dictionary of arguments.
    """
    parser = ArgumentParser()
    parser.add_argument(
        "--xml",
        "-x",
        type=str,
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
        help='List of "My Tags" to be relocated to the Genre field.',
    )
    parser.add_argument(
        "--overwrite_tags",
        "-w",
        action="store_true",
        help='Overwrite Genre field with "My Tags".'
    )
    parser.add_argument(
        "--genre_tag_delimiter",
        "-g",
        type=str,
        default="/",
        help="Character used to separate genre tags.",
    )
    args = parser.parse_args()

    return vars(args)


def move_genre_tags(
    xml: str,
    tags: Set[str],
    output: str,
    overwrite_tags: bool,
    genre_tag_delimiter: str,
):
    """_summary_

    Args:
        xml: Path to a Rekordbox XML file.
        tags: Set of "My Tags" to be moved to the Genre field.
        output: Path to an output Rekordbox XML file.
        overwrite_tags: Whether or not to overwrite pre-existing Genre field.
        genre_tag_delimiter: Character used to delimit Genre field tags.

    Raises:
        FileNotFoundError: `xml` must be a file that exists.
        Exception: `xml` must be a valid XML file.
    """
    if not os.path.exists(xml):
        raise FileNotFoundError(f'The XML path "{xml}" does not exist!')

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
        # Filter "My Tags" for tags belonging to the provided set of tags
        # to be relocated to the Genre field.
        new_genre_tags = [
            x.strip() for x in my_tags.group().split("/") if x.strip() in tags
        ]
        if not new_genre_tags:
            continue
        # Get pre-existing Genre tags and split them on the chosen delimiter.
        current_genre_tags = [
            x.strip() for x in track["Genre"].split(genre_tag_delimiter)
        ]
        # Deduplicate tags across pre-existing Genre tags and "My Tags".
        if current_genre_tags and not overwrite_tags:
            new_genre_tags = set(current_genre_tags).union(set(new_genre_tags))
        # Write new tags to Genre field.
        track["Genre"] = f" {genre_tag_delimiter} ".join(new_genre_tags)

    # Write output rekordbox.xml to file.
    with open(output, mode="wb", encoding=db.orignal_encoding) as _file:
        _file.write(db.prettify("utf-8"))


if __name__ == "__main__":
    """Move the provided "My Tags" to the Genre field.

    Raises:
        RuntimeError: the --tags option must contain one or more "My Tags" to
            relocate to the Genre field.
    """
    args = parse_args()
    if not args["tags"]:
        raise RuntimeError(
            'The --tags option must include a list of "My Tag" to move from'
            "the Comments field to the Genre field."
        )
    args["tags"] = set(args["tags"])
    move_genre_tags(
        xml=args["xml"],
        tags=args["tags"],
        output=args["output"],
        overwrite_tags=args["overwrite_tags"],
        genre_tag_delimiter=args["genre_tag_delimiter"],
    )
