"""
Script utility functions
"""

import csv
import hashlib
import logging
import os
import time

from swiftclient.service import ClientException, SwiftError, SwiftService, SwiftUploadObject


# Build the Swift ID - based on Islandora Bagger settings
def generate_aip_id(id):
    return f"aip_{id}.zip"

# Build the path string to the islandora-bagger generated AIP/BAG file
def generate_aip_path(aip_dir, id):
    return f"{aip_dir}/{generate_aip_id(id)}"

#
def upload_aip(node_list, aip_dir, swift_options, container_dst, database_csv) :

    with SwiftService() as swift_conn_dst :
        with open(database_csv, 'w', newline='') as db_file :
            dst_objs = []
            db_writer = csv_init(db_file)
            for key, item_values in node_list.items() :
                aip_path = generate_aip_path(aip_dir, key)
                aip_id = generate_aip_id(key)
                logging.info(f"  uploading: {aip_path}")
                checksums = file_checksum(aip_path)
                item_options = {
                    'header' : {
                        'x-object-meta-sha256sum': checksums['sha256sum'],
                        'x-object-meta-last-mod-timestamp': item_values['changed'],
                        'content-type': item_values['content_type']
                        }
                    }
                dst_objs.append(build_swift_upload_object(aip_id, aip_path, swift_options, item_options))
                upload(swift_conn_dst, dst_objs, container_dst, db_writer)
            os.fsync(db_file)

#
def validate(node_list, swift_container) :

    with SwiftService() as swift_conn_dst :
        for key, src_value in node_list.items() :
            aip_id = generate_aip_id(key)
            logging.info(f"  Validating: {aip_id}")
            swift_stat = swift_conn_dst.stat(swift_container, [aip_id])
            if (swift_stat):
                for dst in swift_stat:
                    logging.debug(f"{dst}")
                    if (dst['success'] == False):
                        logging.error(f"id:[{aip_id}] - preservation error [{dst['error']}]")
                        logging.error(f"id:[{aip_id}] - swift stat - [{dst}]")
                        break
                    elif (src_value['changed'] != dst['headers']['x-object-meta-last-mod-timestamp']):
                        logging.error(f"id:[{aip_id}] - mismatched modification timestamp [{src_value['changed']}] : {dst['headers']['x-object-meta-last-mod-timestamp']}")
                        break
            else:
                logging.error(f"key:[{aip_id}] - not present in destination: {swift_stat}")


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
        # test if segmented large object: https://docs.openstack.org/swift/newton/overview_large_objects.html
        if dst_item['action'] == 'upload_object':
            logging.debug(f"{dst_item}")
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

#
def audit(node_list, aip_dir, swift_container) :
    with SwiftService() as swift_conn_dst :
        for id, item_values in node_list.items() :

            # test if AIP in path
            aip_path = generate_aip_path(aip_dir, id)
            aip_id = generate_aip_id(id)
            logging.info(f"  Audit: {aip_id}")
            if (not(os.path.exists(aip_path))):
                logging.error(f"id:[{id}] - missing AIP [{aip_path}]")
                continue

            aip_mtime = os.path.getmtime(aip_path)
            aip_time = time.gmtime(aip_mtime)

            if (aip_time < time.strptime(item_values['changed'],"%Y-%m-%dT%H:%M:%S%z")):
                logging.error(f"id:[{id}] - filesystem date older than source date [{aip_time}] - [{item_values['changed']}]")
                continue

            # test if AIP in OLRC
            swift_stat = swift_conn_dst.stat(swift_container, [aip_id])
            if (swift_stat):
                for dst in swift_stat:
                    logging.debug(f"{dst}")
                    if (dst['success'] == False):
                        logging.error(f"id:[{id}] - preservation error [{dst['error']}]")
                        logging.error(f"id:[{id}] - swift stat - [{dst}]")
                        break
                    if (item_values['changed'] != dst['headers']['x-object-meta-last-mod-timestamp']):
                        logging.error(f"id:[{id}] - mismatched modification timestamp [{item_values['changed']}] : [{dst['headers']['x-object-meta-last-mod-timestamp']}]")
                        break
                    checksums = file_checksum(aip_path)
                    if (checksums['sha256sum'] != dst['headers']['x-object-meta-sha256sum']):
                        logging.error(f"id:[{id}] - mismatched checksum [{checksums['sha256sum']}] : [{dst['headers']['x-object-meta-sha256sum']}]")
                        break
            else:
                logging.error(f"key:[{id}] - not present in destination: {swift_stat}")

