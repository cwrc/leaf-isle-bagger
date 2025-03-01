##############################################################################################
# desc: connect to a Drupal instance, get a list of Drupal Nodes and Media that have changed
#       since a supplied date and return a list of Drupal Nodes (e.g., to preserve in an
#       AIP - archival information package)
# usage: python3 leaf-bagger.py \
#          --server ${server_name} \
#          --output ${output_path} \
#          --date '2024-05-16T16:51:52' \
#          --container 'test' \
# license: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication
# date: May 15, 2024
##############################################################################################

import argparse
import logging
import os
import pathlib

from drupal import api as drupalApi
from drupal import utilities as drupalUtilities
from swift import utilities as swiftUtilities


#
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True, help="Server name.")
    parser.add_argument(
        "--output", required=True, help="Location to store CSV output file."
    )
    parser.add_argument(
        "--error_log",
        required=False,
        default=None,
        help="Location to store error logs.",
    )
    parser.add_argument(
        "--date", required=False, help="Items changed after the given date."
    )
    parser.add_argument(
        "--container",
        required=False,
        help="OpenStack Swift container to upload into.",
        default="cwrc_test",
    )
    parser.add_argument(
        "--wait",
        required=False,
        help="Time to wait between API calls.",
        type=float,
        default=0.1,
    )
    parser.add_argument(
        "--logging_level", required=False, help="Logging level.", default=logging.INFO
    )
    parser.add_argument(
        "--bagger_app_dir",
        required=False,
        help="Path to the Bag creation tool.",
        default=os.getenv("BAGGER_APP_DIR"),
    )
    parser.add_argument(
        "--aip_dir",
        required=False,
        help="Path to the Archival Information Packages (AIPs/BAGs).",
        default=f"{os.getenv('BAGGER_OUTPUT_DIR')}",
    )
    parser.add_argument(
        "--force_single_node",
        required=False,
        help="Override node selection and process only the specified item.",
        default="",
    )
    return parser.parse_args()


#
def process(args, session):

    # a list of resources to preserve
    node_list = {}

    # get a list of Drupal Node IDs either from specified ID or via a list
    if args.force_single_node:
        node_list = drupalUtilities.id_list_from_arg(session, args)
        logging.info(f"AIP: Drupal node before media inclusion - {node_list}")
        # inspect associated Drupal Media for changes
        # a Media change does not transitively update the associated Node change timestamp
        # if Media changed but not the associated Node then add associated Node ID to the list
        drupalUtilities.single_node_merge_with_media(
            session, args.server, node_list, args.force_single_node
        )
        logging.info(f"AIP: Drupal node with media changes - {node_list}")
    else:
        # get a list of Drupal Node IDs changed since a given optional date
        # or a single node then force update
        node_list = drupalUtilities.id_list_from_nodes(session, args)
        logging.info(f"AIP: Drupal nodes before media inclusion - {node_list}")
        # inspect associated Drupal Media for changes
        # a Media change does not transitively update the associated Node change timestamp)
        # if Media changed but not the associated Node then add associated Node ID to the list
        drupalUtilities.id_list_merge_with_media(session, args, node_list)
        logging.info(f"AIP: Drupal nodes with media changes - {node_list}")

    # create archival information packages
    logging.info("Create AIPs")
    drupalUtilities.create_aip(node_list, args.bagger_app_dir)

    # upload archival information packages
    logging.info("Upload AIPs")
    options = {
        "header": {
            "x-object-meta-project-id": "",
            "x-object-meta-aip-version": "",
            "x-object-meta-project": "",
            "x-object-meta-promise": "",
        }
    }
    swiftUtilities.upload_aip(
        node_list, args.aip_dir, options, args.container, args.output
    )

    # validate archival information packages
    logging.info("Validate Upload")
    swiftUtilities.validate(node_list, args.container)


#
def main():

    args = parse_args()

    # Create logging handlers
    logging_handlers = [logging.StreamHandler()]
    if args.error_log is not None:
        logging_handlers.append(logging.FileHandler(args.error_log))

    # Config Logging
    logging.basicConfig(level=args.logging_level, handlers=logging_handlers)
    logging.getLogger("swiftclient").setLevel(logging.CRITICAL)

    username, password = drupalUtilities.get_drupal_credentials()

    session = drupalApi.init_session(args, username, password)

    pathlib.Path(os.path.dirname(args.output)).mkdir(parents=True, exist_ok=True)
    process(args, session)


if __name__ == "__main__":
    main()
