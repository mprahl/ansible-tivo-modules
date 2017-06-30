# Ansible Tivo Modules

A repository of Ansible modules that help manage your Tivo related tasks.

### fetch_tivo_recordings
Downloads recordings from a Tivo device and optionally formats the file names
to a standard format based on information from The TVDB.

Options:
* **hostname**: The IP address or hostname of the Tivo device
* **mak**: The MAK/Media Access Key of the Tivo device. This is used for
authentication.
* **title**: The title of the recording to download (e.g a TV show, movie, etc.)
* **episode**: The episode name of the recording to download. If this is not set,
all episodes of the series specified will be downloaded.
* **dest_dir**: The directory to download the recordings in. This must already
exist.
* **tvdb_api_key**: The API key from The TVDB which is used to find the season
and episode numbers of recordings. If not set, they will not be in the file
names.
* **tvdb_user_key**: The user key from The TVDB. This is found in the account
settings page.
* **tvdb_username**: The username from The TVDB
* **tvdb_ignore_failure**: Determines whether or not to fail the module if the
recording is not found in the TVDB. This only applies if the recording is an
episode.

This module requires the following Python modules:
* requests
