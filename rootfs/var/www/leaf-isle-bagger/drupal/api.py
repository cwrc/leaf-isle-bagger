"""
Drupal API utility functions
"""

import requests

from urllib.parse import urljoin


# initialize a session with API endpoint
def init_session(args, username, password):

    session = requests.Session()
    # session.auth = (username, password)

    auth_endpoint = "user/login?_format=json"
    response = session.post(
        urljoin(args.server, auth_endpoint),
        json={"name": username, "pass": password},
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()

    return session


#
def node_view_endpoint(page=0, date_filter=""):
    return f"views/preservation_show_node_timestamps?page={page}&changed={date_filter}"


#
def get_node_list(session, server, page=0, date_filter=""):

    response = session.get(
        urljoin(server, node_view_endpoint(page, date_filter)),
        # allow_redirects=config["allow_redirects"],
        # verify=config["secure_ssl_only"],
        # auth=(config["username"], config["password"]),
        # params=config["query"],
        # headers=config["headers"],
    )
    response.raise_for_status()
    return response


#
def media_view_endpoint(page=0, date_filter=""):
    return f"views/preservation_show_media_timestamps?page={page}&changed={date_filter}"


#
def get_media_list(session, server, page=0, date_filter=""):
    response = session.get(
        urljoin(server, media_view_endpoint(page, date_filter)),
    )
    response.raise_for_status()
    return response


#
def get_node_by_format(session, server, item_id):
    response = session.get(
        urljoin(server, f"node/{item_id}?_format=json"),
    )
    response.raise_for_status()
    return response

def media_associated_with_node_endpoint(id):
    return f"node/{id}/media?_format=json"

#
def get_associated_media_by_format(session, server, id):
    response = session.get(
        urljoin(server, media_associated_with_node_endpoint(id))
    )
    response.raise_for_status()
    return response
