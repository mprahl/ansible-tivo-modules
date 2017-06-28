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

import os
import subprocess as sp

from ansible.module_utils.basic import AnsibleModule

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'supported_by': 'community',
    'status': ['preview']
}

DOCUMENTATION = '''
---
module: strip_tivo_protection
short_description: Strips Tivo files to standard MPEG format
description:
  - >
    Removes the protection from Tivo files and outputs them to standard MPEG
    format by using TivoDecoder by fflewddur.
options:
  mak:
    description:
      - >
        The MAK/Media Access Key of the Tivo device. This is used to remove
        the protection on the Tivo files.
    required: true
  tivo_decoder_path:
    description:
      - The path to TivoDecorder.jar.
    required: false
    default: /opt/tivo/TivoDecoder.jar
  source:
    description:
      - The Tivo recording to strip or a folder of .TiVo files to strip.
    required: true
  destination:
    description:
      - >
        The destination file path for the stripped Tivo recording or the
        folder to place all stripped Tivo recordings to.
    required: false
  replace:
    description:
      - Delete the source .TiVo file(s).
    required: false
    default: false
'''

EXAMPLES = '''
# Strip a single Tivo recording
- strip_tivo_protection:
    mak: {mak}
    source: /home/user/recording.TiVo

# Strip a folder of Tivo recordings and delete the .TiVo files
- strip_tivo_protection:
    mak: {mak}
    source: /home/user/videos/
    replace: true

# Strip a folder of Tivo recordings and place them in a different folders
- strip_tivo_protection:
    mak: {mak}
    source: /home/user/videos/
    destination: /mnt/NAS/Videos/
'''.format(mak='0123456789')

# Make the module global
module = None


def tivo_to_mpg(mak, source, destination=None,
                tivo_decoder_path='/opt/tivo/TivoDecoder.jar'):
    """
    Uses TivoLibre to convert a .tivo file to .mpg
    :param mak: a string of the Tivo's media access key
    :param source: a string of the path to convert
    :param destination: a string of the destination file. If not set, it will
    be the same directory as the source.
    :param tivo_decoder_path: a string to the path of TivoDecoder.jar. This
    defaults to `/opt/tivo/TivoDecoder.jar`.
    :return: a string of the destination file or None if the file was skipped.
    """
    if destination:
        destination_path = destination
    else:
        destination_path = source.rsplit('.', 1)[0] + '.mpg'

    if os.path.exists(destination_path):
        return None

    command = ['java', '-jar', tivo_decoder_path, '-i', source, '-o',
               destination_path, '-m', mak]
    decoder_proc = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE)
    stdout, stderr = decoder_proc.communicate()
    if decoder_proc.returncode != 0:
        msg = ('The TivoDecoder command failed. The following was called '
               '"{0}" and the error was "{1}"'.format(
                   ' '.join(command), stderr))
        module.fail_json(msg=msg)

    return destination_path


def main():
    """
    The main function where the module starts
    :return: None
    """
    global module
    module = AnsibleModule(
        argument_spec={
            'mak': {'required': True, 'type': 'str'},
            'tivo_decoder_path': {'default': '/opt/tivo/TivoDecoder.jar',
                                  'type': 'str'},
            'source': {'required': True, 'type': 'str'},
            'destination': {'required': False, 'type': 'str'},
            'replace': {'default': False, 'type': 'bool'}
        },
        supports_check_mode=False
    )
    source = module.params['source']
    destination = module.params.get('destination')
    tivo_decoder_path = module.params['tivo_decoder_path']
    mak = module.params['mak']
    replace = module.params['replace']

    if not os.path.exists(tivo_decoder_path):
        msg = 'TivoDecoder.jar was not found at "{0}"'.format(
            tivo_decoder_path)
        module.fail_json(msg=msg)

    if not os.path.exists(source):
        module.fail_json(msg='The source does not exist')

    source_is_dir = os.path.isdir(source)
    if destination:
        dest_exists = os.path.exists(destination)
        dest_is_dir = os.path.isdir(destination)
        if dest_exists and dest_is_dir != source_is_dir:
            msg = 'The source and destination need to be the same type'
            module.fail_json(msg=msg)

    videos_to_strip = []
    if source_is_dir:
        for item in os.listdir(source):
            full_path = os.path.join(source, item)
            if item.lower().endswith('.tivo') and os.path.isfile(full_path):
                videos_to_strip.append(full_path)
    else:
        videos_to_strip.append(os.path.abspath(source))

    videos_stripped = 0
    for video in videos_to_strip:
        if tivo_to_mpg(mak, video, destination, tivo_decoder_path):
            videos_stripped += 1
            if replace:
                os.remove(video)

    if videos_stripped > 0:
        success_msg = '{0} recording(s) stripped successfully'.format(
            videos_stripped)
        module.exit_json(msg=success_msg, changed=True)
    else:
        if len(videos_to_strip) > 0:
            msg = '{0} recordings were skipped'.format(len(videos_to_strip))
        else:
            msg = 'No recordings were found that matched the criteria'
        module.exit_json(msg=msg, changed=False)


if __name__ == '__main__':
    main()
