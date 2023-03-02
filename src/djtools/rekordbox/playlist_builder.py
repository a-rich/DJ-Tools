"""This module is used to automatically generate a playlist structure using
genre tags and the "My Tags" Rekordbox feature. It also supports creating
"Combiner" playlists with arbitrary boolean algebra using:
    * "(" and ")" groupings
    * "&", "|", and "~" operators
    * playlist selectors, e.g. "{My favorite playlist}"
    * BPM selectors, e.g. "[80-90, 140, 165-174]"
    * Rating selectors, e.g. "[1, 2-4"
    * tag names (genre or "My Tags")

NOTE: In order for "My Tags" to be stored in the exported XML files, users must
enable the 'Add "My Tag" to the "Comments"' setting under
"Preferences > Advanced > Browse".
"""
from collections import defaultdict
import logging
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Union

import bs4
from bs4 import BeautifulSoup
import yaml

from djtools.configs.config import BaseConfig
from djtools.rekordbox import tag_parsers
from djtools.rekordbox.tag_parsers import Combiner


logger = logging.getLogger(__name__)


class PlaylistBuilder:
    """This class writes an XML Rekordbox database with auto-playlists.
    
    The XML written by this class  will contain auto-generated playlists using
    configurations found in "rekordbox_playlists.yaml".

    The "rekordbox_playlists.yaml" configuration file maps implemented
    TagParsers to a playlist taxonomy. Currently supported TagParsers are:
        * GenreTagParser: reads "Genre" field of tracks and creates a list of
            tags splitting on "/" characters. 
        * MyTagParser: reads "Comments" field of tracks and searches for the
            regex pattern /* tag_1 / tag_2 / tag_3 */
            and creates a list of tags splitting on "/" characters.
    
    A "rekordbox_playlists.yaml" configuration file may also contain a
    "Combiner" key which is distinct from a TagParser implementation.
    Rather than parse tags, this class accepts the constructed tag -> track
    mapping and applies boolean algebra to create playlists using operators:
        * AND (designated with "&"): result set will contain tracks having both tags.
        * OR (designated with "|"): result set will contain tracks having either tag.
        * NOT (designated with "~"): result set will not contain tracks having this tag.
        * "()": encloses a grouping of operators which are evaluated first.
        * "{}": encloses a playlist name to select those tracks. 
        * "[]": encloses a comma-delimited list of integers representing
            ratings (1 through 5) or BPMs (numbers greater than 5); ranges can
            be specified by separating two integers with a dash.
    """
    def __init__(
        self,
        rekordbox_database: Union[str, Path],
        playlist_config: Union[str, Path],
        pure_genre_playlists: List[str] = [],
        playlist_remainder_type: str = "",
    ):
        """Constructor.

        Args:
            rekordbox_database: Path to Rekordbox XML.
            playlist_config: Playlist taxonomy.
            pure_genre_playlists: Create one or more "pure" playlists which
                have only tracks with tags containing these substrings.
            playlist_remainder_type: Whether unspecified tags are grouped into
                a "folder" or "playlist".

        Raises:
            AttributeError: Configured TagParser must be implemented in
                "tag_parsers.py".
        """
        # Load Rekordbox database from XML.
        self._database_path = rekordbox_database
        with open(self._database_path, mode="r", encoding="utf-8") as _file:
            self._database = BeautifulSoup(_file.read(), "xml")

        # Get playlist root node.
        self._playlists_root = self._database.find_all(
            "NODE", {"Name": "ROOT", "Type": "0"}
        )[0]

        # Create folder for auto-playlists.
        self._auto_playlists_root = self._database.new_tag(
            "NODE", Name="AUTO_PLAYLISTS", Type="0"
        )

        # Whether tags unspecified in playlist taxonomies are grouped into an
        # "Other" "folder" or "playlist".
        self._playlist_remainder_type = playlist_remainder_type

        # Create TagParsers from rekordbox_playlists.yaml.
        with open(playlist_config, mode="r", encoding="utf-8") as _file:
            self._playlist_config = (
                yaml.load(_file, Loader=yaml.FullLoader) or {}
            )
        self._parsers = {}
        self._combiner_parser = None
        for playlist_type, config in self._playlist_config.items():
            try:
                parser = getattr(tag_parsers, playlist_type)
            except AttributeError:
                raise AttributeError(
                    f"{playlist_type} is not a valid TagParser!"
                )

            parser = parser(
                parser_config=config,
                pure_genre_playlists=pure_genre_playlists,
                rekordbox_database=self._database,
            )

            # "Combiner" class used to assemble playlists by applying
            # boolean algebra to tags.
            if isinstance(parser, Combiner):
                self._combiner_parser = parser
                continue

            self._parsers[playlist_type] = parser

    def __call__(self):
        """Generates auto-playlists by:
            * creating playlists nodes
            * generating tags -> tracks mapping
            * inserting tags to the appropriate playlist nodes for "Genre" and
                "My Tags" playlists
            * applying "Combiner" boolean algebra to tags
            * writting new XML database
        """
        tracks = {k: defaultdict(list) for k in self._parsers}
        playlists = {} 
        for track in self._database.find_all("TRACK"):
            if not track.get("Location"):
                continue
            for playlist_type, parser in self._parsers.items():
                # Initialize each type of playlist with a node and tag set.
                if playlist_type not in playlists:
                    tag_set = set()
                    playlists[playlist_type] = {
                        "tags": tag_set,
                        "playlists": self._create_playlists(
                            soup=self._database,
                            content=parser.parser_config,
                            tags=tag_set,
                            top_level=True,
                        ) 
                    }

                # Create tags -> tracks map.
                tags = parser(track)
                for tag in tags:
                    tracks[playlist_type][tag].append((track["TrackID"], tags))
        
        # Add tracks to their respective playlists.
        for playlist_type, playlist_data in playlists.items():
            if self._playlist_remainder_type:
                # Insert tracks otherwise not captured by the configuration's
                # playlist taxonomy into "Other" groupings.
                self._add_other(
                    soup=self._database,
                    remainder_type= self._playlist_remainder_type,
                    tags=playlist_data["tags"],
                    tracks=tracks[playlist_type],
                    playlists=playlist_data["playlists"],
                )
            
            # Insert tracks into their respective playlists.
            self._add_tracks(
                soup=self._database,
                playlists=playlist_data["playlists"],
                tracks=tracks[playlist_type],
            )
            
            # Insert playlist node into the playlist root.
            self._auto_playlists_root.insert(0, playlist_data["playlists"])
        
        if self._combiner_parser:
            # Create Combiner playlist structure.
            combiner_playlists = self._create_playlists(
                soup=self._database,
                content=self._combiner_parser.parser_config,
                top_level=True,
            ) 

            # Reduce track tags across parsers unioning when there is overlap.
            merged_tracks = defaultdict(list)
            for values in tracks.values():
                for k, v in values.items():
                    merged_tracks[k].extend(v)

            # Use the most up-to-date Rekordbox database to update the track
            # lookup with playlist selectors to their component tracks.
            playlist_mapping = self._combiner_parser.get_playlist_mapping(
                self._auto_playlists_root
            )
            merged_tracks.update(playlist_mapping)

            # Evaluate the boolean logic of the Combiner playlists.
            tracks = self._combiner_parser(merged_tracks)

            # Insert tracks into their respective playlists.
            self._add_tracks(
                soup=self._database,
                playlists=combiner_playlists,
                tracks=tracks,
            )

            # Insert playlist node into the playlist root.
            self._auto_playlists_root.insert(0, combiner_playlists)

        # Decompose irrelevant playlists.
        for node in self._playlists_root.find_all("NODE"):
            if node.attrs and node.attrs["Name"] != "ROOT":
                node.decompose()
        
        # Insert the auto-playlists into the playlists root.
        self._playlists_root.insert(0, self._auto_playlists_root)

        # Write XML file.
        _dir, _file = os.path.split(self._database_path)
        auto_xml_path = os.path.join(_dir, f"auto_{_file}").replace(os.sep, "/")
        with open(
            auto_xml_path, mode="wb", encoding=self._database.orignal_encoding
        ) as _file:
            _file.write(self._database.prettify("utf-8"))

    def _add_other(
        self,
        soup: BeautifulSoup,
        remainder_type: str,
        tags: Set[str],
        tracks: Dict[str, List[Tuple[str, List[str]]]],
        playlists: bs4.element.Tag,
    ):
        """Identifies the remainder tags by taking the set difference of all
            track tags with those that appear in "rekordbox_playlists.yaml". If
            "remainder_type" is "playlist", then all these tracks are inserted
            into an "Other" playlist. If "remainder_type" is "folder", then an
            "Other" folder is created and playlists for each tag are populated.

        Args:
            soup: Parsed XML.
            remainder_type: Whether to put tags not specified in folder with
                individual playlists for each tag or into a single "Other"
                playlist.
            tags: All the tags in "rekordbox_playlists.yaml".
            tracks: Map of tags to lists of (track_id, tags) tuples.
            playlists: Empty playlist structure.
        """
        if remainder_type == "folder":
            folder = soup.new_tag("NODE", Name="Other", Type="0")
            for other in sorted(set(tracks).difference(tags)):
                playlist = soup.new_tag("NODE", Name=other, Type="1", KeyType="0")
                folder.append(playlist)
            playlists.append(folder)
        elif remainder_type == "playlist":
            playlist = soup.new_tag(
                "NODE", Name="Other", Type="1", KeyType="0"
            )
            playlists.append(playlist)
        else:
            logger.error(f'Invalid remainder type "{remainder_type}"')

    def _add_tracks(
        self,
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
                if playlist.parent["Name"] == "Genres":
                    pure_hip_hop = True
                else:
                    bass_hip_hop = True

            for entry in tracks.get(playlist["Name"], []):
                if isinstance(entry, tuple):
                    track_id, tags = entry
                else:
                    track_id = entry
                    tags = []
                # NOTE: Special logic to distinguish between the general "Hip Hop"
                # playlist (a.k.a. pure Hip Hop) and the "Hip Hop" playlist under
                # the "Bass" folder (a.k.a. bass Hip Hop)
                if (pure_hip_hop and any(
                        "r&b" not in x.lower() and "hip hop" not in x.lower()
                        for x in tags
                    )
                ) or (bass_hip_hop and all(
                        "r&b" in x.lower() or "hip hop" in x.lower()
                        for x in tags
                    )
                ):
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
                        # NOTE(a-rich): not covered by tests.
                        # if _seen_index not in seen:
                        #     seen[_seen_index] = set()

                        if track_id not in seen[_seen_index]:
                            _all.append(soup.new_tag("TRACK", Key=track_id))
                            seen[_seen_index].add(track_id)
                    except IndexError:
                        break
                    parent = parent.parent
            
    def _create_playlists(
        self,
        soup: BeautifulSoup,
        content: Union[str, Dict],
        tags: Set[str] = set(),
        top_level: bool = False,
    ) -> bs4.element.Tag:
        """Recursively traverses "rekordbox_playlists.yaml" and creates the
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
            ValueError: "rekordbox_playlists.yaml" must be properly formatted.

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
                    _playlist = self._create_playlists(
                        soup=soup, content=playlist, tags=tags
                    )
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


def rekordbox_playlists(config: BaseConfig):
    """Runs the PlaylistBuilder.

    Args:
        config: Configuration object.
    """
    playlist_config = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "configs",
        "rekordbox_playlists.yaml",
    ).replace(os.sep, "/")

    playlist_builder = PlaylistBuilder(
        rekordbox_database=config.XML_PATH,
        playlist_config=playlist_config,
        pure_genre_playlists=config.PURE_GENRE_PLAYLISTS,
        playlist_remainder_type=config.REKORDBOX_PLAYLISTS_REMAINDER,
    )
    playlist_builder()
