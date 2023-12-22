# Welcome to DJ Tools

DJ Tools started out as a set of scripts used to sync audio files to the cloud so I could share tracks with my friends. It's since grown into a Python library with many features for streamlining the processes around collecting, curating, and sharing a music collection.

This library is DJ-platform agnostic. That being said, a subset of features (those under the `collection` package) depend on implementations for `Collection`, `Playlist`, and `Track` abstractions (see the [references](reference/collection/)) for which there are currently only Rekordbox implementations. If you're interested in adding implementations for other DJ platforms, please create an [issue](https://github.com/a-rich/DJ-Tools/issues).

DJ Tools is built and tested on Unix-based operating systems. I try my best to test everything on Windows as well, but your mileage may very.

## Where to start
Check out the [Getting Started](tutorials/getting_started/index.md) tutorial!

## How do I...?
Every capability of DJ Tools is demonstrated in the [How-to Guides](how_to_guides/index.md). Additionally, there are some guides for things external to DJ Tools such as [setting up object storage](how_to_guides/setup_object_storage.md) and getting [access to the Reddit and Spotify APIs](how_to_guides/reddit_spotify_api_access.md).

## Tell me more
You'll find exposition on relevant topics in [Conceptual Guides](conceptual_guides/index.md) such as [Get to Know Your Rekordbox Collection](conceptual_guides/rekordbox_collection.md), [Tagging Guide](conceptual_guides/tagging_guide.md), and [The Importance of Standardization and Quality Control](conceptual_guides/file_standardization.md).

### [Interested in contributing](https://github.com/a-rich/DJ-Tools/blob/main/CONTRIBUTING.md)?
