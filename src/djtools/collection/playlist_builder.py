"This module is used to automatically generate a playlist structure."
import logging
from collections import defaultdict
from pathlib import Path
from typing import Optional, Type

from djtools.collection import playlist_filters
from djtools.collection.config import PlaylistConfig, PlaylistConfigContent
from djtools.collection.helpers import (
    add_selectors_to_tags,
    aggregate_playlists,
    build_combiner_playlists,
    build_tag_playlists,
    filter_tag_playlists,
    print_playlists_tag_statistics,
)
from djtools.collection.platform_registry import PLATFORM_REGISTRY
from djtools.utils.helpers import make_path


logger = logging.getLogger(__name__)
PLAYLIST_NAME = "PLAYLIST_BUILDER"
BaseConfig = Type["BaseConfig"]


@make_path
def collection_playlists(config: BaseConfig, path: Optional[Path] = None):
    """Builds playlists automatically.

    By maintaining a collection with tracks having tag data (e.g. genre tags,
    Rekordbox's "My Tags", etc.) and providing a playlist config which
    specifies a desired playlist structure based around these tags, users can
    automatically generate that playlist structure.

    The playlist config is a YAML file which specifies a nested structure of
    folders. Each folder is declared with a "name" and a list of "playlists"
    which may be either more folder declarations or else strings matching a tag
    in your collection.

    Any folder that has more than one playlist within it will automatically
    have an "All <folder name>" playlist added to it that contains the set of
    tracks from all the other playlists in that folder.

    Any tag in your collection that is not specified in the playlist config
    will automatically be added to either an "Other" folder of playlists or an
    "Other" playlist (depending on your configured choice for
    collection_playlists_remainder).

    A special folder with the name "_ignore" may be included anywhere within
    the "tags" specification with playlists matching the set of tags to ignore
    when creating the "Other" folder / playlist.

    In addition to creating playlists from tags, this function also supports
    creating "combiner" playlists by evaluating boolean algebra expressions.
    This is an incredibly powerful feature which allows users to apply set
    operations {union, intersection, and difference} to a diverse range of
    operands {tag, playlists, BPMs, ratings, etc.}.

    Combiner playlists are declared in the "combiner" specification of the
    playlist config with playlists whose names are the boolean algebra
    expressions used to construct them.

    Here's an example combiner playlist to illustrate this:

        ((Dubstep ~ [1-3]) | {playlist: My Favorites} | (*Techno & [135-145])) & Dark

    The resulting combiner playlist will be comprised of tracks that are:

    - tagged as "Dubstep" but NOT having a rating less than 4
    - OR in the playlist called "My Favorites"
    - OR tagged as something ending with "Techno" AND in the BPM range of 135
    to 145
    - AND tagged as "Dark"

    Args:
        config: Configuration object.
        path: Path to write the new collection to.
    """
    config.collection.playlist_config = PlaylistConfig(
        **config.collection.playlist_config or {}
    )

    # Check if the playlist config is populated before continuing.
    if not (
        config.collection.playlist_config.tags
        or config.collection.playlist_config.combiner
    ):
        logger.warning(
            "Not building playlists because the playlist config is empty."
        )
        return

    # Load the collection.
    collection = PLATFORM_REGISTRY[config.collection.platform]["collection"](
        path=config.collection.collection_path
    )

    # Get the Playlist implementation to use for this collection.
    playlist_class = PLATFORM_REGISTRY[config.collection.platform]["playlist"]

    # Required number of tracks to make tag and combiner playlists.
    minimum_tag_tracks = config.collection.minimum_tag_playlist_tracks
    minimum_combiner_tracks = (
        config.collection.minimum_combiner_playlist_tracks
    )

    # Create a dict of tracks keyed by their individual tags.
    tags_tracks = defaultdict(dict)
    for track_id, track in collection.get_tracks().items():
        for tag in track.get_tags():
            tags_tracks[tag][track_id] = track

    # This will hold the playlists being built.
    auto_playlists = []

    # List of PlaylistFilter implementations to run against built playlists.
    filters = [
        getattr(playlist_filters, playlist_filter)()
        for playlist_filter in config.collection.collection_playlist_filters
    ]

    # Create playlists for the "tags" portion of the playlist config.
    if config.collection.playlist_config.tags:
        # A set of tags seen is maintained while creating the tags playlists so
        # that they are ignored when creating the "Other" playlists.
        seen_tags = set()
        tag_playlists = build_tag_playlists(
            config.collection.playlist_config.tags,
            tags_tracks,
            playlist_class,
            seen_tags,
            minimum_tracks=minimum_tag_tracks,
        )

        # The tag playlists must have their "parent" attribute set so that
        # PlaylistFilter implementations may apply logic that depends on the
        # relative position of the playlist with the playlist tree.
        tag_playlists.set_parent()

        # Apply the filtering logic of the configured PlaylistFilter implementations.
        filter_tag_playlists(tag_playlists, filters)

        # Recursively traverse the playlist tree and create "all" playlists
        # within each folder containing more than one playlist. These "all"
        # playlists aggregate the set of tracks contained within all the other
        # playlists within the same folder.
        _ = aggregate_playlists(
            tag_playlists, playlist_class, minimum_tag_tracks
        )

        auto_playlists.extend(tag_playlists)

        # Identify the set of tags that did not appear in the playlist config
        # and create either an "Other" folder of playlists or simply an "Other"
        # playlist.
        other_tags = sorted(set(tags_tracks).difference(seen_tags))
        if config.collection.collection_playlists_remainder == "folder":
            auto_playlists.append(
                build_tag_playlists(
                    PlaylistConfigContent(
                        name="Unused Tags", playlists=other_tags
                    ),
                    tags_tracks,
                    playlist_class,
                    minimum_tracks=minimum_tag_tracks,
                )
            )
        else:
            auto_playlists.append(
                build_tag_playlists(
                    "Unused Tags",
                    {
                        "Unused Tags": {
                            track_id: track
                            for tag, track_dict in tags_tracks.items()
                            for track_id, track in track_dict.items()
                            if tag in other_tags
                        }
                    },
                    playlist_class,
                    minimum_tracks=minimum_tag_tracks,
                )
            )

    # Create playlists for the "combiner" portion of the playlist config.
    if config.collection.playlist_config.combiner:
        # Parse selectors from the combiner playlist names and update the
        # tags_tracks mapping.
        add_selectors_to_tags(
            config.collection.playlist_config.combiner,
            tags_tracks,
            collection,
            auto_playlists,
        )

        # Evaluate the boolean logic of the combiner playlists.
        combiner_playlists = build_combiner_playlists(
            config.collection.playlist_config.combiner,
            tags_tracks,
            playlist_class,
            minimum_tracks=minimum_combiner_tracks,
        )

        # The tag playlists must have their "parent" attribute set so that
        # PlaylistFilter implementations may apply logic that depends on the
        # relative position of the playlist with the playlist tree.
        combiner_playlists.set_parent()

        # Apply the filtering logic of the configured PlaylistFilter implementations.
        filter_tag_playlists(combiner_playlists, filters)

        # Recursively traverse the playlist tree and create "all" playlists
        # within each folder containing more than one playlist. These "all"
        # playlists aggregate the set of tracks contained within all the other
        # playlists within the same folder.
        _ = aggregate_playlists(
            combiner_playlists, playlist_class, minimum_combiner_tracks
        )

        auto_playlists.extend(combiner_playlists)

        # Print tag statistics for each combiner playlist.
        if config.verbosity and combiner_playlists:
            print_playlists_tag_statistics(combiner_playlists)

    # Remove any previous playlist builder playlists.
    previous_playlists = collection.get_playlists(name=PLAYLIST_NAME)
    root = collection.get_playlists()
    for playlist in previous_playlists:
        root.remove_playlist(playlist)

    # Insert a new playlist containing the built playlists.
    auto_playlist = playlist_class.new_playlist(
        name=PLAYLIST_NAME, playlists=auto_playlists
    )
    auto_playlist.set_parent(collection.get_playlists())
    collection.add_playlist(auto_playlist)
    collection.serialize(path=path)

    num_playlists = collection.get_playlists().get_number_of_playlists()
    logger.info(f"{PLAYLIST_NAME} generated with {num_playlists} playlists")
