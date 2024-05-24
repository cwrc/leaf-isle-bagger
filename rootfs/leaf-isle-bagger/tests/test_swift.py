"""
Test the OpenStack Swift integration module
"""

import csv
import logging
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
_aip_dir = 'rootfs/leaf-isle-bagger/tests/assets/fixtures'

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

# Test validation
# https://docs.pytest.org/en/latest/how-to/logging.html#caplog-fixture
def test_validation(caplog, mocker) :
    node_list = {1: {'changed': '2025-01-01', 'content_type': 'application/zip'}}
    mocker.patch('leaf-bagger.swiftUtilities.SwiftService.stat', return_value=[
            {
                'headers' : { 'x-object-meta-last-mod-timestamp' : '2025-01-01' }
            }
        ])
    with caplog.at_level(logging.ERROR):
        swiftUtilities.validate(node_list)
        for record in caplog.records:
            assert record.levelname != "ERROR"

# Test validation: fail on date
def test_validation_date_mismatch(caplog, mocker) :
    node_list = {1: {'changed': '2025-01-01', 'content_type': 'application/zip'}}
    mocker.patch('leaf-bagger.swiftUtilities.SwiftService.stat', return_value=[
            {
                'headers' : { 'x-object-meta-last-mod-timestamp' : '2024-01-01' }
            }
        ])
    with caplog.at_level(logging.ERROR):
        swiftUtilities.validate(node_list)
        for record in caplog.records:
            assert record.levelname == "ERROR"
        assert "mismatched modification timestamp" in caplog.text

# Test validation: fail on missing id
def test_validation_id_mismatch(caplog, mocker) :
    node_list = {1: {'changed': '2025-01-01', 'content_type': 'application/zip'}}
    mocker.patch('leaf-bagger.swiftUtilities.SwiftService.stat', return_value=[
        ])
    with caplog.at_level(logging.ERROR):
        swiftUtilities.validate(node_list)
        for record in caplog.records:
            assert record.levelname == "ERROR"
        assert "not present in destination" in caplog.text

# Test Audit
def test_audit(caplog, mocker) :
    node_list = {1: {'changed': '2024-01-01T01:01:01', 'content_type': 'application/zip'}}
    mocker.patch('leaf-bagger.swiftUtilities.SwiftService.stat', return_value=[
            {
                'headers' : {
                    'x-object-meta-last-mod-timestamp' : '2024-01-01T01:01:01',
                    'x-object-meta-sha256sum' : '4e7c226ea38f60bd4187c6d0dd8f73463643d56fba46c1efd38c634a99d8cd40',
                    'etag' : ''
                    }
            }
        ])
    with caplog.at_level(logging.ERROR):
        swiftUtilities.audit(node_list, _aip_dir)
        for record in caplog.records:
            assert record.levelname != "ERROR"

# Test validation: fail on preservation date
def test_audit_date_mismatch(caplog, mocker) :
    node_list = {1: {'changed': '2024-01-01T01:01:01', 'content_type': 'application/zip'}}
    mocker.patch('leaf-bagger.swiftUtilities.SwiftService.stat', return_value=[
            {
                'headers' : {
                    'x-object-meta-last-mod-timestamp' : '2026-01-01',
                    'x-object-meta-sha256sum' : '4e7c226ea38f60bd4187c6d0dd8f73463643d56fba46c1efd38c634a99d8cd40',
                    'etag' : ''
                    }
            }
        ])
    with caplog.at_level(logging.ERROR):
        swiftUtilities.audit(node_list, _aip_dir)
        for record in caplog.records:
            assert record.levelname == "ERROR"
        assert "mismatched modification timestamp" in caplog.text

# Test validation: fail on file date
def test_audit_date_mismatch_file(caplog, mocker) :
    node_list = {1: {'changed': '9999-01-01T01:01:01', 'content_type': 'application/zip'}}
    mocker.patch('leaf-bagger.swiftUtilities.SwiftService.stat', return_value=[
            {
                'headers' : {
                    'x-object-meta-last-mod-timestamp' : '2026-01-01',
                    'x-object-meta-sha256sum' : '4e7c226ea38f60bd4187c6d0dd8f73463643d56fba46c1efd38c634a99d8cd40',
                    'etag' : ''
                    }
            }
        ])
    with caplog.at_level(logging.ERROR):
        swiftUtilities.audit(node_list, _aip_dir)
        for record in caplog.records:
            assert record.levelname == "ERROR"
        assert "filesystem date older than source date" in caplog.text

# Test validation: fail on file checksum
def test_audit_checksum(caplog, mocker) :
    node_list = {1: {'changed': '2024-01-01T01:01:01', 'content_type': 'application/zip'}}
    mocker.patch('leaf-bagger.swiftUtilities.SwiftService.stat', return_value=[
            {
                'headers' : {
                    'x-object-meta-last-mod-timestamp' : '2024-01-01T01:01:01',
                    'x-object-meta-sha256sum' : '0',
                    'etag' : ''
                    }
            }
        ])
    with caplog.at_level(logging.ERROR):
        swiftUtilities.audit(node_list, _aip_dir)
        for record in caplog.records:
            assert record.levelname == "ERROR"
        assert "mismatched checksum" in caplog.text



# Test validation: fail on missing id
def test_audit_id_mismatch(caplog, mocker) :
    node_list = {1: {'changed': '2024-01-01T01:01:01', 'content_type': 'application/zip'}}
    mocker.patch('leaf-bagger.swiftUtilities.SwiftService.stat', return_value=[
        ])
    with caplog.at_level(logging.ERROR):
        swiftUtilities.audit(node_list, _aip_dir)
        for record in caplog.records:
            assert record.levelname == "ERROR"
        assert "not present in destination" in caplog.text

