##############################################################################################
# desc: connect to a Drupal instance, get a list of Drupal Nodes and Media that have changed
#       since a supplied date and return a list of Drupal Nodes (e.g., to preserve in an
#       AIP - archival information package)
# usage: python3 get_node_id.py --server ${server_name} --output ${output_path} --date '2024-05-16T16:51:52'
# license: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication
# date: June 15, 2022
##############################################################################################

from getpass import getpass
from time import sleep
import argparse
import json
import logging
import os

from drupal import api as drupalApi
from drupal import utilities as drupalUtilities

#
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', required=True, help='Servername.')
    parser.add_argument('--output', required=True, help='Location to store JSON (like) output file.')
    parser.add_argument('--date', required=False, help='Items changed after the given date.')
    parser.add_argument('--wait', required=False, help='Time to wait between API calls.', type=float, default=0.1)
    parser.add_argument('--logging_level', required=False, help='Logging level.', default=logging.WARNING)
    return parser.parse_args()


#
def process(args, session, output_file):

    # a list of resources to preserve
    node_list = {}

    # get a list of Drupal Node IDs changed since a given optional date
    node_list = drupalUtilities.id_list_from_nodes(session, args)
    print(node_list)

    # inspect Drupal Media for changes
    # a Media change is does not transitively change the associated Node change timestamp)
    # if Media changed then add associated Node ID to the list
    drupalUtilities.id_list_merge_with_media(session, args, node_list)
    print(node_list)

    # create archival information packages
    drupalUtilities.create_aip(node_list, args.BAGGER_APP_PATH)

    # upload archival information packages
#
def main():
    args = parse_args()
    args['BAGGER_APP_PATH'] = os.getenv('BAGGER_APP_PATH')

    username = input('Username:')
    password = getpass('Password:')

    session = drupalApi.init_session(args, username, password)

    with open(args.output, 'wt', encoding="utf-8", newline='') as output_file:
        process(args, session, output_file)


if __name__ == "__main__":
    main()