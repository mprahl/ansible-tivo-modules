# Ansible Tivo Modules

A repository of Ansible modules that help manage your Tivo related tasks.

### fetch_tivo_recordings
Downloads recordings from a Tivo device and optionally formats the file names
to a standard format based on information from The TVDB.

Options:
* **hostname**: The IP address or hostname of the Tivo device
* **mak**: The MAK/Media Access Key of the Tivo device. This is used for
authentication. This must be a string in the YAML file.
* **title**: The title of the recording to download (e.g a TV show, movie,
etc.)
* **episode**: The episode name of the recording to download. If this is not
set, all episodes of the series specified will be downloaded.
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
* **skip_if_in_path**: The path to check if a recording of the same name
(without the file extension) exists before downloading the recording. If this
is not set, the check will be bypassed.

This module requires the following Python modules:
* requests


### strip_tivo_protection
Uses [TivoDecoder](https://github.com/fflewddur/tivolibre) to remove the
protection on .TiVo files and outputs a standard MPG file.

Options:
* **mak**: The MAK/Media Access Key of the Tivo device. This is used to remove
the protection on the Tivo files. This must be a string in the YAML file.
* **tivo_decoder_path**: The path to TivoDecorder.jar. This defaults to
"/opt/tivo/TivoDecoder.jar".
* **source**: The Tivo recording to strip or a folder of .TiVo files to strip.
* **destination**: The destination file path for the stripped Tivo recording or
the folder to place all stripped Tivo recordings to.
* **replace**: Delete the source .TiVo file(s). This defaults to false.


### convert_and_cut_recordings
Uses [comskip](https://github.com/erikkaashoek/Comskip) and ffmpeg to remove
commercials from a TV recording and convert it to an mp4.

Options:
* **source**: The video or folder of mpg videos to convert.
* **destination**: The destination file path for the output video file or the
folder to place all output video files to.
* **replace**: Delete the original files.
* **destination**: The destination file path for the stripped Tivo recording or
the folder to place all stripped Tivo recordings to.
* **replace**: Delete the original files. This defaults to false.
* **video_codec**: The ffmpeg video codec to use. See the
[ffmpeg documentation](https://www.ffmpeg.org/general.html#Video-Codecs) for a
list codecs to chose from.
* **video_quality**: The ffmpeg crf value to chose from that determines video
quality. See the
[libx265 documenation](https://trac.ffmpeg.org/wiki/Encode/H.265#ConstantRateFactorCRF)
or [libx264 documentation](https://trac.ffmpeg.org/wiki/Encode/H.264#crf) for
more details.
* **audio_codec**: The ffmpeg audio codec to use. See the
[ffmpeg documentation](https://www.ffmpeg.org/general.html#Audio-Codecs) for a
list codecs to chose from.
* **audio_quality**: The constant bit rate in KB that determines audio quality.
See the [ffmpeg documentation](https://trac.ffmpeg.org/wiki/Encode/AAC#fdk_cbr)
for more details.
* **compression_speed**: The ffmpeg compression speed preset to use when
converting the video. See the [ffmpeg documenation](https://trac.ffmpeg.org/wiki/Encode/H.265#ConstantRateFactorCRF) for more
details.
* **comskip_path**: The path to the comskip binary, which is used to cut
commercials. This defaults to `/opt/tivo/comskip`.
* **comskip_ini**: The path to the comskip.ini file to use with comskip. If
this is not set, commercials will not be cut.
