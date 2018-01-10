#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# (c) 2017, Matt Prahl
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software. If not, see <http://www.gnu.org/licenses/>.

from os import path, listdir
import json
import re
import xml.etree.ElementTree as ET
from time import sleep

import requests
from requests.exceptions import ConnectionError, ConnectTimeout
from requests.auth import HTTPDigestAuth
from six.moves.urllib_parse import urlencode
from ansible.module_utils.basic import AnsibleModule

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'supported_by': 'community',
    'status': ['preview']
}

DOCUMENTATION = '''
---
module: fetch_tivo_recordings
short_description: Downloads recordings from a Tivo device
description:
  - >
    Downloads recordings from a Tivo device and optionally formats the file
    names to a standard format based on information from The TVDB
options:
  hostname:
    description:
      - The IP address or hostname of the Tivo device
    required: true
  mak:
    description:
      - >
        The MAK/Media Access Key of the Tivo device. This is used for
        authentication.
    required: true
  title:
    description:
      - The title of the recording to download (e.g a TV show, movie, etc.)
    required: true
  episode:
    description:
      - >
        The episode name of the recording to download. If this is not set,
        all episodes of the series specified will be downloaded.
    required: false
  dest_dir:
    description:
      - The directory to download the recordings in. This must already exist.
    required: True
  tvdb_api_key:
    description:
      - >
        The API key from The TVDB which is used to find the season and
        episode numbers of recordings. If not set, they will not be in the
        file names.
    required: false
  tvdb_user_key:
    description:
      - >
        The user key from The TVDB. This is found in the account settings
        page.
    required: false
  tvdb_username:
    description:
      - The username from The TVDB
    required: false
  tvdb_ignore_failure:
    description:
      - >
        Determines whether or not to fail the module if the recording is not
        found in the TVDB. This only applies if the recording is an episode.
    required: false
    default: false
  skip_if_in_path:
    description:
      - >
        The path to check if a recording of the same name (without the file
        extension) exists before downloading the recording. If this is not set,
        the check will be bypassed.
    required: false
requirements: ["requests"]
'''

EXAMPLES = '''
# Download a movie
- fetch_tivo_recordings:
    hostname: {hostname}
    mak: {mak}
    title: Toy Story
    dest_dir: {dest_dir}

# Download a series without season and episode numbers in the file name
- fetch_tivo_recordings:
    hostname: {hostname}
    mak: {mak}
    title: {series_title}
    dest_dir: {dest_dir}

# Download a series with season and episode numbers in the file name
- fetch_tivo_recordings:
    hostname: {hostname}
    mak: {mak}
    title: {series_title}
    tvdb_api_key: {tvdb_api_key}
    tvdb_user_key: {tvdb_user_key}
    tvdb_username: {tvdb_user}
    dest_dir: {dest_dir}

# Download an episode with season and episode numbers in the file name
- fetch_tivo_recordings:
    hostname: {hostname}
    mak: {mak}
    title: {series_title}
    episode: Bart the General
    tvdb_api_key: {tvdb_api_key}
    tvdb_user_key: {tvdb_user_key}
    tvdb_username: {tvdb_user}
    dest_dir: {dest_dir}
'''.format(hostname='192.168.1.50', mak='0123456789', tvdb_api_key='123456789',
           tvdb_user_key='34567890123', tvdb_user='jhancock',
           dest_dir='/path/to/dir/', series_title='The Simpsons')

# The Tivo connection will always be untrusted
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning)
# Make the module global
module = None


def requests_wrapper(*args, **kwargs):
    """
    A wrapper around the requests module with error handling
    :param args: Any positional arguments you'd pass to a requests function
    :param kwargs: Any keyword arguments you'd pass to a requests function.
    Additionally, there are special parameters used such as "fail_on_error",
    which will fail the module when an error occurs. There is also "error_msg",
    which is a string used as the failure message, and "http_verb", which
    specifies what action to take on the API. If it's not set, it will default
    to "get".
    :return: a requests object
    """
    if 'fail_on_error' in kwargs:
        fail_on_error = kwargs.pop('fail_on_error')
    else:
        fail_on_error = True
    error_msg = ''
    if 'error_msg' in kwargs:
        error_msg = kwargs.pop('error_msg')
    if 'http_verb' in kwargs:
        action = kwargs.pop('http_verb').lower()
    else:
        action = 'get'
    # If the request is JSON and a dict was passed in as the payload, then
    # convert the string to JSON
    if 'data' in kwargs and isinstance(kwargs['data'], dict) \
            and 'headers' in kwargs and isinstance(kwargs['headers'], dict) \
            and 'json' in kwargs['headers'].get('Content-Type'):
        kwargs['data'] = json.dumps(kwargs['data'])
    requests_function = getattr(requests, action)
    try:
        rv = requests_function(*args, **kwargs)
        if rv.ok:
            return rv
        elif fail_on_error:
            module.fail_json(msg=error_msg)
    except (ConnectionError, ConnectTimeout):
        if fail_on_error:
            module.fail_json(msg=error_msg)
    return None


def get_request_json(rv, error_msg, fail_on_error=True):
    """
    A wrapper to get the JSON from a request object
    :param rv: a request object (e.g. return value of requests.get)
    :param action: a string describing the action for more useful error
    messages
    :param fail_on_error: a boolean that determines if this function should
    fail the module on error
    :return: dictionary of the returned JSON or a ClickException
    """
    if rv.ok:
        return rv.json()
    else:
        error_msg = ('{0} The status code was "{1}". The following was '
                     'returned "{2}"'.format(
                         error_msg, rv.status_code, rv.content))
        if fail_on_error:
            module.fail_json(msg=error_msg)


def get_season_episode_num(api_key, user_key, username, series_name,
                           episode_name, fail_on_error=True):
    """
    Queries The TVDB to get the season and episode numbers
    :param api_key: a string of The TVDB API key
    :param user_key: a string of The TVDB user key
    :param username: a string of The TVDB username
    :param series_name: a string of The TVDB series
    :param episode_name: a string of The TVDB episode
    :param fail_on_error: a boolean to determine if the module should fail if
    the function can't determine the season and episode numbers
    :return: a tuple of the season and episode number
    """
    api_url = 'https://api.thetvdb.com'
    api_login_url = '{0}/login'.format(api_url)
    series_query_api_url = '{0}/search/series?{1}'.format(
        api_url, urlencode({'name': series_name}))
    headers = {'Content-Type': 'application/json'}
    login_payload = {
        'apikey': api_key,
        'userkey': user_key,
        'username': username
    }
    error_msg = 'The request failed attempting to login to The TVDB'
    rv = requests_wrapper(
        api_login_url, headers=headers, data=login_payload, http_verb='post',
        error_msg=error_msg, fail_on_error=fail_on_error, timeout=30)
    # If rv is None, that means the request failed and fail_on_error is set to
    # False
    if not rv:
        return None, None
    rv_json = get_request_json(rv, error_msg, fail_on_error)
    if not rv_json:
        return None, None
    token = rv_json['token']
    headers['Authorization'] = 'Bearer {0}'.format(token)

    error_msg = (u'The request failed while getting the series "{0}" in The '
                 u'TVDB'.format(series_name))
    rv = requests_wrapper(
        series_query_api_url, headers=headers, error_msg=error_msg,
        fail_on_error=fail_on_error, timeout=30)
    if not rv.ok:
        return None, None
    rv_json = get_request_json(rv, error_msg, fail_on_error)
    if not rv_json:
        return None, None
    series_info = rv_json['data'][0]
    series_id = series_info['id']

    tvdb_series_episodes_api_url = \
        '{0}/series/{1}/episodes'.format(api_url, series_id)
    error_msg = ('The request failed getting the episodes in the series "{0}" '
                 'from The TVDB'.format(series_name))
    page = 1
    while True:
        tvdb_series_episodes_api_url_with_queries = '{0}?{1}'.format(
            tvdb_series_episodes_api_url, urlencode({'page': page}))
        rv = requests_wrapper(
            tvdb_series_episodes_api_url_with_queries, headers=headers,
            error_msg=error_msg, fail_on_error=fail_on_error, timeout=30)
        if not rv.ok:
            return None, None
        rv_json = get_request_json(rv, error_msg, fail_on_error)
        if not rv_json:
            return None, None

        for episode in rv_json['data']:
            # Do a case insensitive check since some words can be capitalized
            # differently on the TiVo and The TVDB
            if episode['episodeName'].strip().lower() == episode_name.lower():
                return episode['airedSeason'], episode['airedEpisodeNumber']

        if rv_json['links']['next']:
            page = rv_json['links']['next']
        else:
            if fail_on_error:
                module.fail_json(
                    msg='The episode "{0}" could not be found on The TVDB'
                    .format(episode_name))
            return None, None


def get_tivo_dl_link_from_element(item_element):
    """
    Get the download link from the Tivo recording API element
    :param item_element: XML object of the recording in the API
    :return: a string of the download link of the recording
    """
    try:
        return '{0}&Format=video/x-tivo-mpeg'.format(
            item_element.find('Links').find('Content').find('Url').text)
    except:
        module.fail_json(
            msg='The data received from Tivo was in an unexpected format')


def get_tivo_recording_info(hostname, mak, title, episode=None):
    """
    Get the recording information from the Tivo API
    :param hostname: a string of the hostname/IP to the Tivo
    :param mak: a string of the Tivo's MAK/Media Access Key
    :param title: a string of the recording title (series title, movie title,
    etc.)
    :param episode: a string of the episode title
    :return: a dictionary with information on the recording
    """
    base_url = ('https://{0}/TiVoConnect?Command=QueryContainer&Container=%2F'
                'NowPlaying&Recurse=Yes'.format(hostname))
    error_msg = 'The request to get the recordings from Tivo failed.'
    recordings = []
    offset = 0
    while True:
        tivo_url = '{0}&AnchorOffset={1}'.format(base_url, offset)
        rv = requests_wrapper(tivo_url, verify=False, error_msg=error_msg,
                              auth=HTTPDigestAuth('tivo', mak), timeout=60)

        # Strip out the namespace for convenience in queries later on
        xml_content = re.sub(r' xmlns="[^"]+"', '', rv.content.decode('utf-8'),
                             count=1)
        # Get an XML object
        xml_root = ET.fromstring(xml_content.encode('utf-8'))
        item_count = int(xml_root.findtext('ItemCount'))
        if item_count == 0:
            break

        # Loop through all the "Item" tags
        for child in xml_root.iter('Item'):
            # If the "Item" tag doesn't have a child tag of "Details", then
            # it's not a tag with recording information
            child_details = child.find('Details')
            if child_details is None:
                continue
            # Check to see if the title of this section matches the desired]
            # title, if not, go to the next recording
            current_title = child_details.find('Title').text
            if current_title != title:
                continue

            # At this point we have the right title (e.g. show name or movie
            # name). If the user specified an episode to download, then let's
            # make sure this is the correct episode.
            episode_element = child_details.find('EpisodeTitle')
            if episode_element is not None:
                # If the user didn't specify an episode or it's the desired
                # episode
                if not episode or episode == episode_element.text:
                    recordings.append({
                        'title': title,
                        'episode': episode_element.text,
                        'link': get_tivo_dl_link_from_element(child)
                    })

                    if episode:
                        # Since the user specified a single episode, that is
                        # all that needs to be returned
                        return recordings
            elif episode_element is None and episode is None:
                # The user didn't specify an episode, and there is no episode
                # value
                recordings.append({
                    'title': title,
                    'link': get_tivo_dl_link_from_element(child)
                })
                # We can return here since there are no episodes associated
                # with this title, so it'll be the only one on the Tivo
                return recordings
        offset += item_count
    return recordings


def download_tivo_recording(mak, recording_info, dest_dir, skip_path=None):
    """
    Downloads the recording from Tivo
    :param mak: a string of the Tivo's MAK/Media Access Key
    :param recording_info: a dictionary returned from get_tivo_recording_info
    :param dest_dir: a string of the folder to download the recording to
    :param skip_path: a string of the folder to check if a recording of the
    same name (without the extension) exists before downloading the recording
    :return: a boolean on if the episode was downloaded or skipped
    """
    season_num = recording_info.get('season_num')
    episode_num = recording_info.get('episode_num')
    title = recording_info['title']
    episode = recording_info.get('episode')
    if season_num and episode_num:
        file_name = u'{0} - S{1:0=2d}E{2:0=2d} - {3}.TiVo'.format(
            title, season_num, episode_num, episode)
    elif episode:
        file_name = u'{0} - {1}.TiVo'.format(title, episode)
    else:
        file_name = u'{0}.TiVo'.format(title)

    if skip_path and path.isdir(skip_path):
        file_name_no_ext = path.splitext(file_name)[0]
        for item in listdir(skip_path):
            # If there is a file with the same name (no ext), skip this
            # recording
            if path.isfile(path.join(skip_path, item)):
                item_no_ext = path.splitext(item)[0]
                if item_no_ext == file_name_no_ext:
                    return False

    dest_file_path = path.join(dest_dir, file_name)
    if path.exists(dest_file_path):
        return False
    if episode:
        error_msg = (u'Downloading the episode "{0}" from the series "{1}"'
                     u'failed.'.format(title, episode))
    else:
        error_msg = u'Downloading "{0}" failed.'.format(title)
    tivo_recording_file = requests_wrapper(
        recording_info['link'], verify=False, error_msg=error_msg,
        auth=HTTPDigestAuth('tivo', mak), timeout=120, stream=True)

    with open(dest_file_path, 'wb') as f:
        for chunk in tivo_recording_file.iter_content(chunk_size=4096):
            if chunk:
                f.write(chunk)
    return True


def main():
    """
    The main function where the module starts
    :return: None
    """
    global module
    module = AnsibleModule(
        argument_spec={
            'hostname': {'required': True, 'type': 'str'},
            'mak': {'required': True, 'type': 'str'},
            'title': {'required': True, 'type': 'str'},
            'episode': {'required': False, 'type': 'str'},
            'dest_dir': {'required': True, 'type': 'str'},
            'tvdb_api_key': {'required': False, 'type': 'str'},
            'tvdb_user_key': {'required': False, 'type': 'str'},
            'tvdb_username': {'required': False, 'type': 'str'},
            'tvdb_ignore_failure': {'required': False, 'type': 'bool',
                                    'default': False},
            'skip_if_in_path': {'required': False, 'type': 'str'}
        },
        supports_check_mode=False
    )
    dest_dir = module.params['dest_dir']
    if not path.isdir(dest_dir):
        module.fail_json(
            msg='The directory "{0}" does not exist'.format(dest_dir))
    recordings_info = get_tivo_recording_info(
        module.params['hostname'], module.params['mak'],
        module.params['title'], module.params['episode'])
    if not recordings_info:
        module.fail_json(msg='No recordings were found')

    tvdb_api_key = module.params['tvdb_api_key']
    tvdb_user_key = module.params['tvdb_user_key']
    tvdb_username = module.params['tvdb_username']
    skip_path = module.params['skip_if_in_path']
    mak = module.params['mak']
    download_count = 0

    for recording_info in recordings_info:
        title = recording_info.get('title')
        episode_name = recording_info.get('episode')
        if episode_name and tvdb_api_key and tvdb_user_key and tvdb_username:
            season_num, episode_num = get_season_episode_num(
                module.params['tvdb_api_key'], module.params['tvdb_user_key'],
                module.params['tvdb_username'], title, episode_name,
                (not module.params['tvdb_ignore_failure']))
            if season_num and episode_num:
                recording_info.update(
                    {'season_num': season_num, 'episode_num': episode_num})

        if download_tivo_recording(mak, recording_info,
                                   module.params['dest_dir'], skip_path):
            download_count += 1
            if download_count < len(recordings_info):
                # Sleep 30 seconds between downloads to give the TiVo a break
                sleep(30)

    if download_count > 0:
        success_msg = '{0} recording(s) downloaded successfully'.format(
            download_count)
        module.exit_json(msg=success_msg, changed=True)
    else:
        if len(recordings_info) > 0:
            msg = '{0} recording(s) skipped'.format(len(recordings_info))
        else:
            msg = 'No recordings were found that matched the criteria'
        module.exit_json(msg=msg, changed=False)


if __name__ == '__main__':
    main()
