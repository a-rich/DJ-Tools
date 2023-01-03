# Sync

## Contents
* Overview
* Setup
* Usage

# Overview
The `sync` package contains a module, `sync_operation`, which can:
* `download_music`: sync files from the `beatcloud` to your `USB_PATH`
* `download_xml`: sync the XML file belonging to `XML_IMPORT_USER` from their folder under `xml` in the `beatcloud` to the parent folder of `XML_PATH`. This operation also rewrites the downloaded XML replacing the track Location fields of `XML_IMPORT_USER` with `USB_PATH` by looking up the `USB_PATH` of `XML_IMPORT_USER` (according to `registered_users.json`).
* `upload_music`: sync files from your `USB_PATH` to the `beatcloud`
* `upload_xml`: sync your `XML_PATH` to your `USER` folder under the `xml` folder in the `beatcloud`


# Setup
The setup required for all these operations is having `awscli` installed and configured to access an AWS S3 instance and a valid `AWS_PROFILE` (`DEFAULT` is the default profile if it wasn't otherwise specified by using the `--profile` option when running `aws configure`).

`NOTE`: other AWS S3 API compliant object-storage solutions, such as [MinIO](https://min.io/), should also work but are untested.

`upload_music` and `download_music` require that `USB_PATH` exists.

`upload_xml` requires that `XML_PATH` exists.

`download_xml` requires that the folder where `XML_PATH` lives exists and that `XML_IMPORT_USER` has run `upload_xml`; it's also required that `XML_IMPORT_USER` has an entry in `registered_users.json` which maps their username i.e `XML_IMPORT_USER` to whatever drive they have set as `USB_PATH`.

# Usage
To run any of the four sync operations {`DOWNLOAD_XML`, `DOWNLOAD_MUSIC`, `UPLOAD_XML`, `UPLOAD_MUSIC`}, just set the corresponding config option to true. If running `DOWNLOAD_XML` make sure `XML_IMPORT_USER` is set to the proper `beatcloud` user. Before uploading / after downloading, you can follow any of the prescribed workflows specified under the main README's "Basic Information" section to ensure consistency both in your local library and in the `beatcloud`.

If the `DOWNLOAD_INCLUDE_SPOTIFY` options is set to the name of a Spotify playlist that exists in your `spotify_playlists.json` config and follows the format `<folder_name> Uploads` where `<folder_name>` matches a top-level folder of "DJ Music" in the beatcloud (ideally should be a user's name), only tracks appearing in that playlist will be downloaded from the Beatcloud.

`NOTE`: you can run `UPLOAD_MUSIC` and / or `DOWNLOAD_MUSIC` with the `--dryrun` flag to inspect the result of the sync operations without actually performing them.
