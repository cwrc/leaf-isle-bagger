"""
Script utility functions
"""

import json
import logging
import os
import subprocess

from getpass import getpass

# local
from drupal import api as drupalApi


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

        if len(node_json) == 0:
            # no more pages
            break
        else:
            for node in node_json:
                add_to_node_list(
                    node_list, node["nid"][0]["value"], node["changed"][0]["value"]
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


# query media as media changes are not reflected as node revisions
# exclude Drupal Media not attached to a Drupal Node
def id_list_merge_with_media(session, args, node_list):

    page = 0
    while True:
        media = drupalApi.get_media_list(session, args.server, page, args.date)
        media_json = json.loads(media.content)

        if len(media_json) == 0:
            # no more pages
            break
        else:
            for media in media_json:
                media_of = None

                if (
                    "field_media_of" in media
                    and len(media["field_media_of"]) >= 1
                    and "target_id" in media["field_media_of"][0]
                ):
                    media_of = media["field_media_of"][0]["target_id"]

                media_changed = (
                    media["changed"][0]["value"] if ("changed" in media) else None
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


def add_to_node_list(node_list, id, changed):
    node_list[id] = {"changed": changed, "content_type": "application/zip"}


# create archival information package
def create_aip(node_list, bagger_app_path):

    for node in list(node_list.keys()):
        # cd ${BAGGER_APP_DIR}
        # ./bin/console app:islandora_bagger:create_bag -vvv --settings=var/sample_per_bag_config.yaml --node=1
        # https://docs.python.org/3/library/subprocess.html
        logging.info(f"  Generating AIP: {node}")
        try:
            subprocess.run(
                [
                    "./bin/console",
                    "app:islandora_bagger:create_bag",
                    "-vvv",
                    "--settings=var/sample_per_bag_config.yaml",
                    f"--node={node}",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=True,
                cwd=bagger_app_path,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"{e}")
        except Exception as e:
            logging.error(f"{e}")
