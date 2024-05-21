"""
Script utility functions
"""

import csv
import hashlib
import logging
import os

from swiftclient.service import ClientException, SwiftError, SwiftService, SwiftUploadObject

#
def upload_aip(node_list, aip_dir, swift_options, container_dst, database_csv) :

    with SwiftService() as swift_conn_dst :
        with open(database_csv, 'w', newline='') as db_file :
            dst_objs = []
            db_writer = csv_init(db_file)
            for key, item_values in node_list.items() :
                item_options = {
                    'header' : {
                        'x-object-meta-last-mod-timestamp': item_values['changed'],
                        'content-type': item_values['content_type']
                        }
                    }
                aip_path = f"{aip_dir}/aip_{key}.zip"
                dst_objs.append(build_swift_upload_object(str(key), aip_path, swift_options, item_options))
                upload(swift_conn_dst, dst_objs, container_dst, db_file)
            os.fsync(db_file)

#
def validate(node_list, aip_dir) :

    with SwiftService() as swift_conn_dst :
        for item in node_list :
            break


def csv_init(fd):
    db_writer = csv.DictWriter(fd, fieldnames=[
        'id',
        'md5sum',
        'sha256sum',
        'uploaded_by',
        'last_updated_at',
        'container_name',
        'notes'
    ])
    db_writer.writeheader()
    return db_writer


#
def build_swift_upload_object(item, aip_path, swift_options, item_options) :

    return SwiftUploadObject(
        aip_path,
        object_name=item,
        options=swift_options|item_options
        )

#
def file_checksum(path):
    hash_md5 = hashlib.md5()
    hash_sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        # read and buffer to prevent high memory usage
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
            hash_sha256.update(chunk)
    return {
        'md5sum': hash_md5.hexdigest(),
        'sha256sum': hash_sha256.hexdigest()
    }

#
def validate_checksum(path, etag, id):
    checksums = file_checksum(path)
    if checksums['md5sum'] != etag:
        raise ClientException(f"ERROR: id:[{id}] error: checksum failure [{path}] - {checksums['md5sum']} <> {etag}")
    return checksums

#
def log_upload(db_writer, dst_item, container_dst, checksums, uploaded_by):
    db_dict = {
        'id': dst_item['object'],
        'md5sum': checksums['md5sum'],
        'sha256sum': checksums['sha256sum'],
        'uploaded_by': uploaded_by,
        'last_updated_at': dst_item['response_dict']['headers']['last-modified'],
        'container_name': container_dst,
        'notes': ""
    }
    db_writer.writerow(db_dict)

#
def upload(swift_conn_dst, dst_objs, container_dst, db_writer=None) :

    for dst_item in swift_conn_dst.upload(container_dst, dst_objs):
        if dst_item['action'] == 'upload_object':
            logging.info(f"{dst_item}")
        if not dst_item['success']:
            if 'object' in dst_item:
                logging.error(f"{dst_item}")
                raise SwiftError(dst_item['error'], container_dst, dst_item['object'])
            # Swift segmented object
            elif 'for_object' in dst_item:
                logging.error(f"{dst_item}")
                raise SwiftError(dst_item['error'], container_dst, dst_item['object'], dst_item['segment_index'])

        if dst_item['action'] == 'upload_object' and os.path.isfile(dst_item['path']):
            # test upload file against Swift header etag to verify
            checksums = validate_checksum(dst_item['path'], dst_item['response_dict']['headers']['etag'], dst_item['object'])
            # log upload
            if db_writer :
                log_upload(db_writer, dst_item, container_dst, checksums, os.getenv('OS_USERNAME'))


