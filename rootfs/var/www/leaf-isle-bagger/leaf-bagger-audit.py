##############################################################################################
# desc: audit leaf-bagger.py:
#       connect to a Drupal instance, get a list of Drupal Nodes and Media that have changed
#       since a supplied date and audit against the leaf-bagger.py created AIPs
# usage: python3 leaf-bagger-audit.py --server ${server_name} --output ${output_path} --date '2024-05-16T16:51:52'
# license: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication
# date: May 15, 2024
##############################################################################################

from getpass import getpass
from time import sleep
import argparse
import json
import logging
import os
import pathlib

from drupal import api as drupalApi
from drupal import utilities as drupalUtilities
from swift import api as swiftApi
from swift import utilities as swiftUtilities

#
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', required=True, help='Server name.')
    parser.add_argument('--output', required=True, help='Location to store JSON (like) output file.')
    parser.add_argument('--date', required=False, help='Items changed after the given date.')
    parser.add_argument('--container', required=False, help='OpenStack Swift container to upload into.', default='cwrc_test')
    parser.add_argument('--wait', required=False, help='Time to wait between API calls.', type=float, default=0.1)
    parser.add_argument('--logging_level', required=False, help='Logging level.', default=logging.INFO)
    parser.add_argument('--bagger_app_dir', required=False, help='Path to the Bag creation tool.', default=f"{os.getenv('BAGGER_OUTPUT_DIR')}")
    return parser.parse_args()


#
def process(args, session, output_file):

    # a list of resources to preserve
    node_list = {}

    # get a list of Drupal Node IDs changed since a given optional date
    node_list = drupalUtilities.id_list_from_nodes(session, args)
    logging.info(node_list)

    # inspect Drupal Media for changes
    # a Media change is does not transitively change the associated Node change timestamp)
    # if Media changed then add associated Node ID to the list
    drupalUtilities.id_list_merge_with_media(session, args, node_list)
    logging.info(node_list)

    # audit archival information packages
    swiftUtilities.audit(output_file, node_list, args.bagger_app_dir, args.container)

#
def main():

    args = parse_args()

    logging.basicConfig(level=args.logging_level)

    username, password = drupalUtilities.get_drupal_credentials()

    session = drupalApi.init_session(args, username, password)

    pathlib.Path(os.path.dirname(args.output)).mkdir(parents=True, exist_ok=True)
    with open(args.output, 'wt', encoding="utf-8", newline='') as output_file:
        audit_fd = swiftUtilities.audit_init(output_file)
        process(args, session, audit_fd)


if __name__ == "__main__":
    main()
