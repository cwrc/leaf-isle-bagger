"""
Test the OpenStack Swift integration module
"""

import csv
import os
import pytest
import pytest_mock
import shutil
import sys

from swiftclient.service import ClientException, SwiftError, SwiftService, SwiftUploadObject

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swift import utilities as swiftUtilities

_object_id = 'a:1'
_swift_download_response = {
    'success': True,
    'path': 'tests/fixtures/assets/a:1',
    'object': _object_id,
    'response_dict': {
        'headers': {
            'etag': '94813657ffbc76defd96ac21ff4061ca',
            'x-object-meta-project-id': 'a',
            'x-object-meta-aip-version': 'b',
            'x-object-meta-project': 'c',
            'x-object-meta-promise': 'd',
            'content-type': 'e',
            'x-object-meta-last-mod-timestamp': 'f'
        }
    }
}

def test_upload_to_destination(tmpdir, mocker):
    # test AIP
    t = { 'path' : f"{tmpdir}/aip_{_object_id}.zip" }
    shutil.copy('rootfs/leaf-isle-bagger/tests/assets/fixtures/aip_1.zip', t['path'])
    upload_obj = [swiftUtilities.build_swift_upload_object(t['path'], _object_id, {}, {})]
    csv_path = tmpdir / "csv"
    with open(csv_path, 'w', newline='') as csv_fd:
        csv_obj = swiftUtilities.csv_init(csv_fd)
        mocker.patch('leaf-bagger.swiftUtilities.SwiftService.upload', return_value=[
            {
                'action': 'upload_object',
                'success': True,
                'path': t['path'],
                'object': _object_id,
                'response_dict': {
                    'headers': {
                        'etag': '94813657ffbc76defd96ac21ff4061ca',
                        'last-modified': 'a'
                    }
                }
            }
        ])
        swiftUtilities.upload(SwiftService, upload_obj, 'CWRC', csv_obj)
    with open(csv_path, 'r', newline='') as tmp_fd:
        dr = csv.DictReader(tmp_fd)
        for row in dr:
            assert row['id'] == _object_id