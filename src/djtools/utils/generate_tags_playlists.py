"""This module is used to automatically generate a playlist structure using
"My Tags" Rekordbox feature.

NOTE: In order for this to work, users must enable the
'Add "My Tag" to the "Comments"' setting under
"Preferences > Advanced > Browse".

When users check one or more of the "My Tags", the corresponding " / "
delimited tags are added to the "Comments" field. Since this field is visible
when users "Export Collection in xml format", it's possible to construct
arbitrary playlist structures using this data.
"""
from collections import defaultdict
import json
import logging
import os
import re
from typing import Dict, List, Set, Tuple, Union

import bs4
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


def generate_tags_playlists(
    config: Dict[str, Union[List, Dict, str, bool, int, float]]
):
    try:
        xml_path = config["XML_PATH"]
    except KeyError:
        raise KeyError(
            "Using the generate_tags_playlists module requires the config "
            "option XML_PATH"
        ) from KeyError

    if not os.path.exists(xml_path):
        raise FileNotFoundError(f"{xml_path} does not exist!")

    with open(xml_path, encoding="utf-8") as _file:
        soup = BeautifulSoup(_file.read(), "xml")
    playlists_root = soup.find_all("NODE", {"Name": "ROOT", "Type": "0"})[0]
    new_playlists = soup.new_tag("NODE", Name="AUTO_PLAYLISTS", Type="0")

    playlist_config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "configs",
        "generate_tags_playlists.json",
    ).replace(os.sep, "/")
    with open(playlist_config_path, encoding="utf-8") as _file:
        all_playlists = json.load(_file)

    for auto_playlist, playlists in all_playlists.items():
        if auto_playlist not in ["Genres", "My Tags"]:
            logger.error(f'Unsupported auto_playlist type "{auto_playlist}"')
            continue

        tags = set()
        playlists = create_playlists(
            soup, playlists, tags, top_level=True
        )

        tracks = defaultdict(list)
        for track in soup.find_all("TRACK"):
            if not track.get("Location"):
                continue

            if auto_playlist == "Genres":
                tags_ = [x.strip() for x in track["Genre"].split("/")]
                for genre in config.get("GENERATE_GENRE_PLAYLISTS_PURE", []):
                    if all(genre.lower() in x.lower() for x in tags_):
                        tracks[f"Pure {genre}"].append(
                            (track["TrackID"], tags_)
                        )
            elif auto_playlist == "My Tags":
                tags_ = re.search(r"(?<=\/\*).*(?=\*\/)", track.get("Comments"))
                if not tags_:
                    continue
                tags_ = [x.strip() for x in tags_.group().split("/")]

            for tag in tags_:
                tracks[tag].append((track["TrackID"], tags_))

        if config.get("GENERATE_TAGS_PLAYLISTS_REMAINDER"):
            add_other(
                soup,
                config["GENERATE_TAGS_PLAYLISTS_REMAINDER"],
                tags,
                tracks,
                playlists,
                auto_playlist,
            )

        add_tracks(soup, playlists, tracks)
        new_playlists.insert(0, playlists)

    playlists_root.insert(0, new_playlists)
    _dir, _file = os.path.split(xml_path)
    auto_xml_path = os.path.join(_dir, f"auto_{_file}").replace(os.sep, "/")
    with open(
        auto_xml_path, mode="wb", encoding=soup.orignal_encoding
    ) as _file:
        _file.write(soup.prettify("utf-8"))


def create_playlists(
    soup: BeautifulSoup,
    content: Union[str, Dict],
    tags: Set[str],
    top_level: bool = False,
) -> bs4.element.Tag:
    """Recursively traverses "generate_tags_playlists.json" and creates the
        corresponding XML tag structure to be populated with tracks. If a
        folder is encountered, an additional playlist is created called
        "All <folder name>" (this does not apply to the top-level folder). If a
        folder named "_ignore" is encountered, tag playlists specified in the
        associated "playlists" list will not have a tag created for them, but
        the tags will be added to the "My Tags" set so the corresponding
        tracks will be ignored when generating the "Other" folder / playlist.

    Args:
        soup: Parsed XML.
        content: Playlist name or folder name with playlists.
        tags: Playlist "My Tags" set to populate.
        top_level: Flag used to indicate that no "All" playlist should
            be created at the top-level of the playlist tree.

    Raises:
        ValueError: "generate_tags_playlists.json" must be properly
            formatted.

    Returns:
        Populated playlist structure.
    """
    if isinstance(content, dict):
        content = {k.lower(): v for k, v in content.items()}
        if content["name"] == "_ignore":
            tags.update(set(content["playlists"]))
        else:
            folder = soup.new_tag("NODE", Name=content["name"], Type="0")
            if not top_level:
                _all = soup.new_tag(
                    "NODE",
                    KeyType="0",
                    Name=f'All {content["name"]}',
                    Type="1",
                )
                folder.append(_all)
            for playlist in content["playlists"]:
                _playlist = create_playlists(soup, playlist, tags)
                if _playlist:
                    folder.append(_playlist)
            return folder
    elif isinstance(content, str):
        tags.add(content)
        playlist = soup.new_tag("NODE", KeyType="0", Name=content, Type="1")
        return playlist
    else:
        raise ValueError(
            f"Encountered invalid input type {type(content)}: {content}"
        )


def add_other(
    soup: BeautifulSoup,
    remainder_type: str,
    tags: Set[str],
    tracks: Dict[str, List[Tuple[str, List[str]]]],
    playlists: bs4.element.Tag,
    playlist_type: str,
):
    """Identifies the remainder tags by taking the set difference of all
        track tags with those that appear in "generate_tags_playlists.json".
        If "remainder_type" is "playlist", then all these tracks are inserted
        into an "Other" playlist. If "remainder_type" is "folder", then an
        "Other" folder is created and playlists for each tag are populated.

    Args:
        soup: Parsed XML.
        remainder_type: Whether to put tags not specified in folder with
            individual playlists for each tag or into a single "Other"
            playlist.
        tags: All the tags in "generate_tags_playlists.json".
        tracks: Map of tags to lists of (track_id, tags) tuples.
        playlists: Empty playlist structure.
        playlist_type: Either "My Tags" or "Genres".
    """
    if remainder_type == "folder":
        folder = soup.new_tag("NODE", Name=f"Other {playlist_type}", Type="0")
        for other in sorted(set(tracks).difference(tags)):
            playlist = soup.new_tag("NODE", Name=other, Type="1", KeyType="0")
            folder.append(playlist)
        playlists.append(folder)
    elif remainder_type == "playlist":
        playlist = soup.new_tag(
            "NODE", Name=f"Other {playlist_type}", Type="1", KeyType="0"
        )
        playlists.append(playlist)
    else:
        logger.error(f'Invalid remainder type "{remainder_type}"')


def add_tracks(
    soup: BeautifulSoup,
    playlists: bs4.element.Tag,
    tracks: Dict[str, List[Tuple[str, List[str]]]],
):
    """Iterates all the tag playlists in the playlist structure and inserts
        tracks having that tag into the playlist. Additionally
        recursively searches the parent of the "playlist" node for a playlist
        called "All <playlist.parent>". If that exists, the track is also
        inserted into this playlist...

        For example, the "Bass" folder has an "All Bass" playlist, and a folder
        called "DnB" which contains both "All DnB" and "Techstep" playlists;
        any track inserted into "Techstep" will also be inserted into "All DnB"
        and "All Bass".

        If any playlist has a non-unique name, then tracks with a matching
        tag will be inserted into all of those playlists. There is
        special logic regarding the "Hip Hop" playlists. My desired tag
        playlist structure has a "Hip Hop" playlist at the top-level which is
        meant to hold Hip Hop tracks that are traditional (i.e. pure Hip Hop /
        Rap). It also has a "Hip Hop" playlist which resides in the "Hip Hop
        Beats" folder under the "Bass" folder; this playlist is meant to hold
        tracks in which Hip Hop is merely a component among other elements
        (like Space Bass, Trap, etc.). This function will only insert tracks
        into the former playlist if all the tags contain only "R&B"
        and/or "Hip Hop". It will only insert tracks into the latter if at
        least one of the tags does NOT contain "R&B" and "Hip Hop".

    Args:
        soup: Parsed XML.
        playlists: Empty playlist structure.
        tracks: Map of tags to lists of (track_id, tags) tuples.
    """
    seen = {}
    for playlist in playlists.find_all("NODE", {"Type": "1"}):
        seen_index = f'{playlist.parent["Name"]} -> {playlist["Name"]}'
        if seen_index not in seen:
            seen[seen_index] = set()

        # NOTE: Special logic to distinguish between the general "Hip Hop"
        # playlist (a.k.a. pure Hip Hop) and the "Hip Hop" playlist under the
        # "Bass" folder (a.k.a. bass Hip Hop).
        pure_hip_hop = bass_hip_hop = False
        if playlist["Name"] == "Hip Hop":
            if playlist.parent["Name"] == "Tags":
                pure_hip_hop = True
            else:
                bass_hip_hop = True

        for track_id, tags in tracks.get(playlist["Name"], []):
            # NOTE: Special logic to distinguish between the general "Hip Hop"
            # playlist (a.k.a. pure Hip Hop) and the "Hip Hop" playlist under
            # the "Bass" folder (a.k.a. bass Hip Hop)
            skip_add = False
            if pure_hip_hop and \
                    any(
                        "r&b" not in x.lower() and "hip hop" not in x.lower()
                        for x in tags
                    ):
                skip_add = True
            if bass_hip_hop and \
                    all(
                        "r&b" in x.lower() or "hip hop" in x.lower()
                        for x in tags
                    ):
                skip_add = True
            if skip_add:
                continue

            if track_id not in seen[seen_index]:
                playlist.append(soup.new_tag("TRACK", Key=track_id))
                seen[seen_index].add(track_id)

            parent = playlist.parent
            while parent:
                try:
                    _all = parent.find_all(
                        "NODE",
                        {"Name": f'All {parent["Name"]}'},
                        recursive=False,
                    )[0]
                    _seen_index = f'{_all.parent["Name"]} -> {_all["Name"]}'
                    if _seen_index not in seen:
                        seen[_seen_index] = set()

                    if track_id not in seen[_seen_index]:
                        _all.append(soup.new_tag("TRACK", Key=track_id))
                        seen[_seen_index].add(track_id)
                except IndexError:
                    break
                parent = parent.parent
