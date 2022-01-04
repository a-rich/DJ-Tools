# Sync

## Contents
* Overview
* Setup
* Usage

# Overview
The `sync` package contains a module, `sync_operation`, which can:
* `upload_music`: sync files from your `USB_PATH` to the `beatcloud` which do not yet exit at the destination
* `download_music`: sync files from the `beatcloud` to your `USB_PATH` which do not yet exit at the destination
* `upload_xml`: sync your `XML_PATH` to your `USER` folder under the `xml` folder in the `beatcloud`
* `download_xml`: sync the `XML_IMPORT_USER` XML from their folder under the `xml` folder in the `beatcloud` to the folder where your `XML_PATH` is...this operation also rewrites the `XML_IMPORT_USER` XML so that the track locations point to those in your `USB_PATH` by looking up the `USB_PATH` that `XML_IMPORT_USER` has set (according to `registered_users.json`) and replaces it with your own `USB_PATH`.


# Setup
The setup required for all these operations is having `awscli` installed and configured to access an AWS S3 instance and a valid `AWS_PROFILE` (`DEFAULT` is the default profile if it wasn't otherwise specified by using the `--profile` option when running `aws configure`).

`upload_music` and `download_music` require that `USB_PATH` exists.

`upload_xml` requires that `XML_PATH` exists.

`download_xml` requires that the folder where `XML_PATH` lives exists and that `XML_IMPORT_USER` has run `upload_xml`; it's also required that `XML_IMPORT_USER` has an entry in `registered_users.json`...this will be the case if they have ever run `dj_tools.py` with a valid `config.json` and then pushed their changes to `registered_users.json` prior to your most recent pull of `DJ Tools`.

# Usage
To run any of the four sync operations, just add them by name to `SYNC_OPERATIONS`. If running `download_xml` make sure `XML_IMPORT_USER` is set to the proper `beatcloud` user. Before uploading / after downloading, you can follow any of the prescribed workflows specified under the main README's "Basic Information" section to ensure consistency both in your local library and in the `beatcloud`.
