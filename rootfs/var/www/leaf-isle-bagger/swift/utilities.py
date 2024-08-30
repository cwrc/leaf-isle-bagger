"""
Script utility functions
"""

import csv
import hashlib
import logging
import os
import time

from datetime import datetime
from swiftclient.service import (
    ClientException,
    SwiftError,
    SwiftService,
    SwiftUploadObject,
)


# Build the Swift ID - based on Islandora Bagger settings
def generate_aip_id(id):
    return f"aip_{id}.zip"


# Build the path string to the islandora-bagger generated AIP/BAG file
def generate_aip_path(aip_dir, id):
    return f"{aip_dir}/{generate_aip_id(id)}"


#
def upload_aip(node_list, aip_dir, swift_options, container_dst, database_csv):

    with SwiftService() as swift_conn_dst:
        with open(database_csv, "w", newline="") as db_file:
            dst_objs = []
            db_writer = log_init(db_file)
            for key, item_values in node_list.items():
                aip_path = generate_aip_path(aip_dir, key)
                aip_id = generate_aip_id(key)
                logging.info(f"  adding to upload: {aip_path}")
                checksums = file_checksum(aip_path)
                item_options = {
                    "header": {
                        "x-object-meta-sha256sum": checksums["sha256sum"],
                        "x-object-meta-last-mod-timestamp": item_values["changed"],
                        "content-type": item_values["content_type"],
                    }
                }
                dst_objs.append(
                    build_swift_upload_object(
                        aip_id, aip_path, swift_options, item_options
                    )
                )
            # May need to be split into batches of "x" if memory usage is too high
            upload(swift_conn_dst, dst_objs, container_dst, db_writer)
            os.fsync(db_file)


#
def validate(node_list, swift_container):

    with SwiftService() as swift_conn_dst:
        for key, src_value in node_list.items():
            aip_id = generate_aip_id(key)
            logging.info(f"  Validating: {aip_id}")
            swift_stat = swift_conn_dst.stat(swift_container, [aip_id])
            if swift_stat:
                for dst in swift_stat:
                    logging.debug(f"{dst}")
                    if dst["success"] is False:
                        logging.error(
                            f"id:[{aip_id}] - preservation error [{dst['error']}]"
                        )
                        logging.error(f"id:[{aip_id}] - swift stat - [{dst}]")
                        break
                    elif (
                        src_value["changed"]
                        != dst["headers"]["x-object-meta-last-mod-timestamp"]
                    ):
                        logging.error(
                            (
                                f"id:[{aip_id}] - mismatched modification timestamp [{src_value['changed']}]"
                                f" : {dst['headers']['x-object-meta-last-mod-timestamp']}"
                            )
                        )
                        break
            else:
                logging.error(
                    f"key:[{aip_id}] - not present in destination: {swift_stat}"
                )


def log_init(fd):
    db_writer = csv.DictWriter(
        fd,
        fieldnames=[
            "id",
            "md5sum",
            "sha256sum",
            "uploaded_by",
            "last_updated_at",
            "container_name",
            "notes",
        ],
    )
    db_writer.writeheader()
    return db_writer


#
def log_upload(db_writer, dst_item, container_dst, checksums, uploaded_by):
    db_dict = {
        "id": dst_item["object"],
        "md5sum": checksums["md5sum"],
        "sha256sum": checksums["sha256sum"],
        "uploaded_by": uploaded_by,
        "last_updated_at": dst_item["response_dict"]["headers"]["last-modified"],
        "container_name": container_dst,
        "notes": "",
    }
    db_writer.writerow(db_dict)


#
def build_swift_upload_object(item, aip_path, swift_options, item_options):

    return SwiftUploadObject(
        aip_path, object_name=item, options=swift_options | item_options
    )


#
def file_checksum(path):
    hash_md5 = hashlib.md5()
    hash_sha256 = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            # read and buffer to prevent high memory usage
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
                hash_sha256.update(chunk)
    except FileNotFoundError as e:
        logging.error(f"{e}")
    finally:
        return {"md5sum": hash_md5.hexdigest(), "sha256sum": hash_sha256.hexdigest()}


#
def validate_checksum(path, etag, id):
    checksums = file_checksum(path)
    if checksums["md5sum"] != etag:
        raise ClientException(
            f"ERROR: id:[{id}] error: checksum failure [{path}] - {checksums['md5sum']} <> {etag}"
        )
    return checksums


#
def upload(swift_conn_dst, dst_objs, container_dst, db_writer=None):

    for dst_item in swift_conn_dst.upload(container_dst, dst_objs):
        try:
            # test if segmented large object: https://docs.openstack.org/swift/newton/overview_large_objects.html
            if dst_item["action"] == "upload_object":
                logging.info(f"  uploading: {dst_item['object']}")
                logging.debug(f"{dst_item}")
            if not dst_item["success"]:
                if "object" in dst_item:
                    logging.error(f"{dst_item}")
                    raise SwiftError(
                        dst_item["error"], container_dst, dst_item["object"]
                    )
                # Swift segmented object
                elif "for_object" in dst_item:
                    logging.error(f"{dst_item}")
                    raise SwiftError(
                        dst_item["error"],
                        container_dst,
                        dst_item["object"],
                        dst_item["segment_index"],
                    )

            if dst_item["action"] == "upload_object" and os.path.isfile(
                dst_item["path"]
            ):
                # test upload file against Swift header etag to verify
                checksums = validate_checksum(
                    dst_item["path"],
                    dst_item["response_dict"]["headers"]["etag"],
                    dst_item["object"],
                )
                # log upload
                logging.debug(f"swift stat - [{dst_item}]")
                if db_writer:
                    log_upload(
                        db_writer,
                        dst_item,
                        container_dst,
                        checksums,
                        os.getenv("OS_USERNAME"),
                    )
        except Exception as e:
            logging.error(f"swift stat - [{dst_item}]")
            logging.error(f"{e}")


#
def swift_timestamp_to_iso8601(ts):
    return datetime.strptime(ts, "%a, %d %b %Y %H:%M:%S %Z").strftime(
        "%Y-%m-%dT%H:%M:%S%z"
    )


#
def audit_init(fd):
    audit_writer = csv.DictWriter(
        fd,
        fieldnames=[
            "drupal_id",
            "drupal_changed",
            "swift_id",
            "swift_timestamp",
            "swift_meta_changed",
            "swift_bytes",
            "status",
        ],
    )
    audit_writer.writeheader()
    return audit_writer


#
def audit_record(
    audit_writer,
    src_id,
    src_changed,
    swift_id="",
    swift_timestamp="",
    swift_changed="",
    swift_bytes="",
    status="",
):
    db_dict = {
        "drupal_id": src_id,
        "drupal_changed": src_changed,
        "swift_id": swift_id,
        "swift_timestamp": (
            swift_timestamp_to_iso8601(swift_timestamp) if (swift_timestamp) else ""
        ),
        "swift_meta_changed": swift_changed,
        "swift_bytes": swift_bytes,
        "status": status,
    }
    audit_writer.writerow(db_dict)


_AUDIT_STATUS_OK = ""
_AUDIT_STATUS_WARN_AIP_MISSING = "xm"
_AUDIT_STATUS_WARN_AIP_DATE = "xd"
_AUDIT_STATUS_WARN_SWIFT_MISSING = "sm"
_AUDIT_STATUS_WARN_SWIFT_TIMESTAMP = "st"
_AUDIT_STATUS_WARN_SWIFT_CHECKSUM = "sw"


#
def audit(audit_writer, node_list, aip_dir, swift_container):

    with SwiftService() as swift_conn_dst:
        for item_id, item_values in node_list.items():

            aip_id = generate_aip_id(item_id)
            aip_path = generate_aip_path(aip_dir, item_id)
            logging.info(f"  Audit: {item_id} - {aip_id} - {aip_path}")

            # test if AIP in path
            if not (os.path.exists(aip_path)):
                logging.error(f"id:[{item_id}] - missing AIP [{aip_path}]")
                audit_record(
                    audit_writer,
                    item_id,
                    item_values["changed"],
                    status=_AUDIT_STATUS_WARN_AIP_MISSING,
                )
                continue

            # test Drupal and filesystem timestamps
            checksums = file_checksum(aip_path)
            aip_mtime = os.path.getmtime(aip_path)
            aip_time = time.gmtime(aip_mtime)
            if aip_time < time.strptime(item_values["changed"], "%Y-%m-%dT%H:%M:%S%z"):
                logging.error(
                    f"id:[{item_id}] - filesystem date older than source date [{aip_time}] - [{item_values['changed']}]"
                )
                audit_record(
                    audit_writer,
                    item_id,
                    item_values["changed"],
                    status=_AUDIT_STATUS_WARN_AIP_DATE,
                )
                continue

            # stat requires a list argument; only adding one;
            swift_stat = swift_conn_dst.stat(swift_container, [aip_id])
            if swift_stat:
                for dst in swift_stat:

                    logging.debug(f"{dst}")

                    status = ""
                    if dst["success"] is False:
                        # test if AIP in OLRC
                        logging.error(
                            f"id:[{item_id}] - preservation error [{dst['error']}]"
                        )
                        logging.error(f"id:[{item_id}] - swift stat - [{dst}]")
                        audit_record(
                            audit_writer,
                            item_id,
                            item_values["changed"],
                            status=_AUDIT_STATUS_WARN_SWIFT_MISSING,
                        )
                    else:
                        # Swift record found, test properties
                        status = audit_swift_properties(
                            item_id, item_values, dst, checksums, aip_id, aip_path
                        )
                        audit_record(
                            audit_writer,
                            item_id,
                            item_values["changed"],
                            dst["object"],
                            dst["headers"]["last-modified"],
                            dst["headers"]["x-object-meta-last-mod-timestamp"],
                            dst["headers"]["content-length"],
                            status,
                        )

            else:
                # Connection failure
                logging.error(f"key:[{item_id}] - connection error: {swift_stat}")


def audit_swift_properties(item_id, item_values, dst, checksums, aip_id, aip_path):

    if item_values["changed"] != dst["headers"]["x-object-meta-last-mod-timestamp"]:
        # test Drupal and Swift timestamps
        status = _AUDIT_STATUS_WARN_SWIFT_TIMESTAMP
        logging.error(
            (
                f"id:[{item_id}] - mismatched modification timestamp [{item_values['changed']}]"
                f" : [{dst['headers']['x-object-meta-last-mod-timestamp']}]"
            )
        )
    elif (
        "x-object-meta-sha256sum" in dst["headers"]
        and checksums["sha256sum"] != dst["headers"]["x-object-meta-sha256sum"]
    ):
        # test filesystem and Swift checksums
        status = _AUDIT_STATUS_WARN_SWIFT_CHECKSUM
        logging.error(
            (
                f"id:[{item_id}] - mismatched checksum [{checksums['sha256sum']}]"
                f" : [{dst['headers']['x-object-meta-sha256sum']}]"
            )
        )
    else:
        status = _AUDIT_STATUS_OK
        logging.info(f"  Audit success: {item_id} - {aip_id} - {aip_path}")

    return status
