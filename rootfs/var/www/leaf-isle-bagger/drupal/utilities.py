"""
Script utility functions
"""

import json
import logging
import os
import subprocess

from datetime import datetime, timezone
from getpass import getpass

# local
from drupal import api as drupalApi


#
def drupal_to_iso8601(ts: int | str) -> str:
    ts = int(ts) if isinstance(ts, str) else ts
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


#
def get_drupal_credentials():

    if os.getenv("BAGGER_DRUPAL_DEFAULT_ACCOUNT_NAME"):
        username = os.getenv("BAGGER_DRUPAL_DEFAULT_ACCOUNT_NAME")
    else:
        username = input("Username:")

    if os.getenv("BAGGER_DRUPAL_DEFAULT_ACCOUNT_PASSWORD"):
        password = os.getenv("BAGGER_DRUPAL_DEFAULT_ACCOUNT_PASSWORD")
    else:
        password = getpass("Password:")
    return username, password


# build list of ids from Drupal Nodes
def id_list_from_nodes(session, args):

    node_list = {}
    page = 0

    while True:
        node = drupalApi.get_node_list(session, args.server, page, args.date)
        node_json = json.loads(node.content)
        logging.debug(
            "Page %s of node content - count[%s] - %s", page, len(node_json), node_json
        )

        if len(node_json) == 0:
            # no more pages
            break
        else:
            for node in node_json:
                add_to_node_list(
                    node_list, node["nid"], drupal_to_iso8601(node["changed"])
                )
            page += 1

    return node_list


# build list of ids from Drupal Nodes
def id_list_from_arg(session, args):
    node_list = {}
    node = drupalApi.get_node_by_format(session, args.server, args.force_single_node)
    node = json.loads(node.content)
    add_to_node_list(node_list, node["nid"][0]["value"], node["changed"][0]["value"])
    return node_list


# Query Media because media updates are not reflected in associated Node change timestamps
# exclude Drupal Media not attached to a Drupal Node
# Apply only to the single node case
def single_node_merge_with_media(session, server, node_list, node_id):

    try:
        node_id = node_id if isinstance(node_id, int) else int(node_id)
    except ValueError:
        logging.error(f"Invalid node id {node_id}")
    else:
        # Get assocaiated Media
        associated_media_json = drupalApi.get_associated_media_by_format(
            session, server, node_id
        )
        associated_media = json.loads(associated_media_json.content)
        for media in associated_media:
            media_changed = (
                media["changed"][0]["value"] if ("changed" in media) else None
            )
            node = node_list.get(node_id, None)
            if (
                media_changed is not None
                and node is not None
                and node["changed"] < media_changed
            ):
                # media changed but the parent node did not change
                node_list[node_id]["changed"] = media_changed
                logging.info(f"  Updating node list changed date : {node_list}")


# Query Group because media updates are not reflected in associated Node change timestamps
# exclude Drupal Media not attached to a Drupal Node
# Apply only to the single node case
def single_node_merge_with_drupal_group(session, server, node_list, node_id):
    try:
        node_id = node_id if isinstance(node_id, int) else int(node_id)
    except ValueError:
        logging.error(f"Invalid node id {node_id}")
    else:
        # Get assocaiated Media
        associated_json = drupalApi.get_groups_by_node(session, server, node_id)
        associated_group = json.loads(associated_json.content)
        for group in associated_group:
            group_changed = get_changed_date(group)
            node = node_list.get(node_id, None)

            if (
                group_changed is not None
                and node is not None
                and node["changed"] < group_changed
            ):
                # group changed but the parent node did not change
                node_list[node_id]["changed"] = group_changed
                logging.info(f"  Updating node list changed date : {node_list}")


# query media as media changes are not reflected as node revisions
# exclude Drupal Media not attached to a Drupal Node
def id_list_merge_with_media(session, args, node_list):

    page = 0
    while True:
        media = drupalApi.get_media_list(session, args.server, page, args.date)
        media_json = json.loads(media.content)
        logging.debug(
            "Page %s of media content - count[%s] - %s",
            page,
            len(media_json),
            media_json,
        )

        if len(media_json) == 0:
            # no more pages
            break
        else:
            for media in media_json:

                media_of = None
                if "field_media_of" in media and len(media["field_media_of"]) >= 1:
                    media_of = media["field_media_of"]

                media_changed = (
                    drupal_to_iso8601(media["changed"])
                    if ("changed" in media)
                    else None
                )

                if (
                    media_of is not None
                    and media_changed is not None
                    and (
                        media_of not in node_list
                        or node_list[media_of]["changed"] < media_changed
                    )
                ):
                    # media changed but the parent node did not change
                    add_to_node_list(node_list, media_of, media_changed)
            page += 1


#
def get_changed_date(group_relationship):

    group_changed_on = group_relationship.get("group_changed_on", None)
    group_relationship_changed_on = group_relationship.get(
        "group_relationship_changed_on", None
    )

    if not group_changed_on and group_relationship_changed_on:
        return drupal_to_iso8601(group_relationship_changed_on)
    elif group_changed_on and not group_relationship_changed_on:
        return drupal_to_iso8601(group_changed_on)
    elif group_changed_on >= group_relationship_changed_on:
        return drupal_to_iso8601(group_changed_on)
    elif group_changed_on <= group_relationship_changed_on:
        return drupal_to_iso8601(group_relationship_changed_on)
    else:
        return None


# query Drupal Groups as group changes are not reflected as node revisions
# exclude Drupal Groups not attached to a Drupal Node
def id_list_merge_with_drupal_groups(session, args, node_list):

    page = 0
    while True:
        groups = drupalApi.get_drupal_groups_list(session, args.server, page, args.date)
        groups_json = json.loads(groups.content)
        logging.debug(
            "Page %s of group content - count[%s] - %s",
            page,
            len(groups_json),
            groups_json,
        )

        if len(groups_json) == 0:
            # no more pages
            break
        else:
            for group_relationship in groups_json:
                node_id = None
                if (
                    "node_id" in group_relationship
                    and len(group_relationship["node_id"]) >= 1
                ):
                    node_id = group_relationship["node_id"]

                group_changed = get_changed_date(group_relationship)

                if (
                    node_id is not None
                    and group_changed is not None
                    and (
                        node_id not in node_list
                        or node_list[node_id]["changed"] < group_changed
                    )
                ):
                    # group changed but the parent node did not change
                    add_to_node_list(node_list, node_id, group_changed)
            page += 1


def add_to_node_list(node_list, id, changed):
    # Node may have different languages thus appear mulpile times the the preservation node view
    # or may have multiple media associated thus ensure always capture the latest change date for the node
    # to ensure capture the latest version of the resource (node and associated bits) for preservation
    if id in node_list:
        logging.debug(
            f"Node [{id}] exists with changed date [{node_list[id]['changed']}] - incoming change date [{changed}]"
        )
        if node_list[id]["changed"] < changed:
            node_list[id]["changed"] = changed
    else:
        node_list[id] = {"changed": changed, "content_type": "application/zip"}


# create archival information package
def create_aip(node_list, bagger_app_path):

    for node in list(node_list.keys()):
        # cd ${BAGGER_APP_DIR}
        # ./bin/console app:islandora_bagger:create_bag -vvv --settings=var/sample_per_bag_config.yaml --node=1
        # https://docs.python.org/3/library/subprocess.html
        logging.info(f"  Generating AIP: {node}")
        try:
            ret = subprocess.run(
                [
                    "./bin/console",
                    "app:islandora_bagger:create_bag",
                    "--settings=var/sample_per_bag_config.yaml",
                    f"--node={node}",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                cwd=bagger_app_path,
                text=True,
            )
            logging.info(f"  AIP generation for node: {node} stderr: {ret.stderr}")
            if ret.returncode != 0:
                logging.critical(f"STDOUT: {ret.stdout}")
                logging.critical(f"STDERR: {ret.stderr}")
                ret.check_returncode()
        except subprocess.CalledProcessError as e:
            logging.error(f"{e}")
        except Exception as e:
            logging.error(f"{e}")
