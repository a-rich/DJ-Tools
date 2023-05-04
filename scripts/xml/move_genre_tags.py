"""Script for moving data from the Comments field to the Genre field."""
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

    return vars(parser.parse_args())


def move_genre_tags(
    xml: str,
    tags: Set[str],
    output: str,
    overwrite_tags: bool,
    genre_tag_delimiter: str,
):
    """Copies selected tags from the Comments field to the Genre field.

    The provided XML must be an valid XML export:
        `File > Export Collection in xml format`
    
    The provided tags must match exactly the data written to the Comments field
    (case-sensitive). 

    The provided output must be the path to a XML file from which you'll import
    the adjusted data.

    The overwrite tags argument, if set, will replace whatever existed in the
    Genre field prior. If this argument is not set, then:
        * the pre-existing data is split on the genre tag delimiter argument
            (default is a forward slash)
        * the tags in the Comments field which match the set provided with the
            tags argument are unioned with the tags in the Genre field (to
            deduplicate tags)
        * and, finally, the reduced set of tags are, again, joined with the
            genre tag delimiter and written to the Genre field.

    Comments field tags are expected to have the format `/* tag1 / tag2 */`
    which is the way Rekordbox's "My Tag" system writes the data to the
    Comments field.
    
    Rekordbox's "My Tag" system will write data to the Comments field only if
    the following setting is enabled:
        `Preferences > Advanced > Browse > Add "My Tag" to the "Comments"`

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
            database = BeautifulSoup(_file.read(), "xml")
    except Exception as exc:
        raise Exception(
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
    with open(output, mode="wb", encoding=database.orignal_encoding) as _file:
        _file.write(database.prettify("utf-8"))


if __name__ == "__main__":
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
