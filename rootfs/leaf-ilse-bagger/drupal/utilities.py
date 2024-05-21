"""
Script utility functions
"""

import json
import subprocess

from drupal import api as drupalApi

# build list of ids from Drupal Nodes
def id_list_from_nodes(session, args) :

    node_list = {}
    page = 0

    while True:
        node = drupalApi.get_node_list(session, args.server, page, args.date)
        node_json = json.loads(node.content)

        if len(node_json) == 0 :
            break

        else :
            #print(node_json)
            for node in node_json:
                node_list[node["nid"][0]['value']] = { "changed": node['changed'][0]["value"]}
            page+=1

    return node_list


# query media as media changes are not reflected as node revisions
# exclude Drupal Media not attached to a Drupal Node
def id_list_merge_with_media(session, args, node_list) :

    page = 0
    while True :
        media = drupalApi.get_media_list(session, args.server, page, args.date)
        media_json = json.loads(media.content)

        if len(media_json) == 0 :
            break
        else :
            for media in media_json:
                media_of = None
                if "field_media_of" in media and len(media["field_media_of"]) >= 1 and "target_id" in media["field_media_of"][0]:
                    media_of = media["field_media_of"][0]['target_id']
                media_changed = media['changed'][0]["value"] if ("changed" in media) else None
                if media_of is not None and media_changed is not None and media_of not in node_list :
                    # media changed but the parent node did not change
                    node_list[media_of] = { "changed": media_changed}
                elif media_of is not None and media_changed is not None and node_list[media_of]["changed"] < media_changed :
                    node_list[media_of] = { "changed": media_changed}
            page+=1

# create archival information package
def create_aip(node_list, bagger_app_path) :

    for node in node_list :
        # cd ${BAGGER_APP_DIR} && ./bin/console app:islandora_bagger:create_bag -vvv --settings=var/sample_per_bag_config.yaml --node=1
        subprocess.run(
            [ './bin/console', 'app:islandora_bagger:create_bag', '-vvv',  '--settings=var/sample_per_bag_config.yaml',  f'--node={node.key}'],
            stdout=subprocess.PIPE,
            check=True,
            cwd=bagger_app_path
            )