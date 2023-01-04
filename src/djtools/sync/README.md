# Sync

## Contents
* Overview
* Setup
* Usage

# Overview
The `sync` package contains the modules:
* `sync_operations`: performs a variety of operations for syncing files
  - `download_music`: sync audio files from the Beatcloud to `USB_PATH`
  - `download_xml`: sync the XML file belonging to `IMPORT_USER` from their folder under `xml` in the Beatcloud to the parent folder of `XML_PATH`. This operation also rewrites the downloaded XML replacing the track Location fields of `IMPORT_USER` with `USB_PATH` by looking up the `USB_PATH` of `IMPORT_USER` (according to `registered_users.yaml`).
 - `upload_music`: sync audio files from `USB_PATH` to the Beatcloud
 - `upload_xml`: sync `XML_PATH` to your `USER` folder under the `xml` folder in the Beatcloud


# Setup
The setup required for all these operations is having `awscli` installed and configured to access an AWS S3 instance and a valid `AWS_PROFILE` (`default` is the default profile if it wasn't otherwise specified by using the `--profile` option when running `aws configure`).

`NOTE`: other AWS S3 API compliant object-storage solutions, such as [MinIO](https://min.io/), should also work but are untested.

`upload_music` and `download_music` require that `USB_PATH` exists.

`upload_xml` and `download_xml` requires that `XML_PATH` exists.

`download_xml` also requires that the `IMPORT_USER:USB_PATH` mapping exists in `registered_users.yaml`.

# Usage
To run any of the four sync operations {`DOWNLOAD_XML`, `DOWNLOAD_MUSIC`, `UPLOAD_XML`, `UPLOAD_MUSIC`}, just set the corresponding config option to true. If running `DOWNLOAD_XML` make sure `IMPORT_USER` is set to the proper Beatcloud user. Before uploading / after downloading, you can follow any of the prescribed workflows specified under the main README's "Basic Information" section to ensure consistency both in your local library and in the Beatcloud.

If the `DOWNLOAD_SPOTIFY` options is set to the name of a Spotify playlist that exists in your `spotify_playlists.yaml` config and follows the format `<folder_name> Uploads` where `<folder_name>` matches a top-level folder of "DJ Music" in the Beatcloud (ideally should be a user's name), only tracks appearing in that playlist will be downloaded from the Beatcloud.

`NOTE`: you can run `UPLOAD_MUSIC` and / or `DOWNLOAD_MUSIC` with the `--dryrun` flag to inspect the result of the sync operations without actually performing them.
