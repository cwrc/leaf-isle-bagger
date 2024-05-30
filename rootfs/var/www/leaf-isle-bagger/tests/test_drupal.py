"""
Test the Drupal integration module
"""

import argparse
import os
import requests
import requests_mock
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drupal import utilities as drupalUtilities
from drupal import api as drupalApi

# Mock pages of request responses
# https://github.com/jamielennox/requests-mock/tree/master
_session = requests.Session()
_adapter = requests_mock.Adapter()
_session.mount('http://', _adapter)

# Test Drupal node change view reader
def test_drupal_node_change_view(mocker):
    # doesn't work with multiple pages
    #mock_response_page_1 = mocker.MagicMock()
    #mock_response_page_1.configure_mock(
    #    **{
    #        'content': '[ { "nid" : [{"value":1}], "changed" : [{"value": "2024-01-01"}] } ]'
    #    }
    #)
    #mock_response_page_2 = mocker.MagicMock()
    #mock_response_page_2.configure_mock(
    #    **{
    #        'content': '[]'
    #    }
    #)
    #mocker.patch(
    #    'leaf-bagger.drupalApi.get_node_list',
    #    return_value=mock_response
    #    )
    mocker.patch(
        'argparse.ArgumentParser.parse_args',
        return_value=argparse.Namespace(date='2023-01-01', server='http://example.com')
        )
    args = argparse.ArgumentParser.parse_args()
    _adapter.register_uri(
        'GET', f"{args.server}/{drupalApi.node_view_endpoint(page='0', date_filter=args.date)}",
        text = '[ { "nid" : [{"value": 1}], "changed" : [{"value": "2024-01-01"}] } ]'
        )
    _adapter.register_uri(
        'GET', f"{args.server}/{drupalApi.node_view_endpoint(page='1', date_filter=args.date)}",
        text = '[]'
        )
    node_list = drupalUtilities.id_list_from_nodes(_session, args)
    assert node_list[1]
    assert node_list[1]['changed'] == '2024-01-01'

# Test the Drupal media change view reader
def test_drupal_media_change_view(mocker):
    mocker.patch(
        'argparse.ArgumentParser.parse_args',
        return_value=argparse.Namespace(date='2023-01-01', server='http://example.com')
        )
    args = argparse.ArgumentParser.parse_args()
    _adapter.register_uri(
        'GET', f"{args.server}/{drupalApi.media_view_endpoint(page='0', date_filter=args.date)}",
        text = '[ { "changed": [{"value": "2025-01-01"}], "field_media_of": [{"target_id": 1}] } ]'
        )
    _adapter.register_uri(
        'GET', f"{args.server}/{drupalApi.media_view_endpoint(page='1', date_filter=args.date)}",
        text = '[]'
        )
    node_list={}
    print(node_list)
    drupalUtilities.id_list_merge_with_media(_session, args, node_list)
    print(node_list)
    assert node_list[1]
    assert node_list[1]['changed'] == '2025-01-01'

# When media is updated the associated node is not updated;
# test that the date list captures the media date not the node date
def test_drupal_media_change_without_node(mocker) :
    mocker.patch(
        'argparse.ArgumentParser.parse_args',
        return_value=argparse.Namespace(date='2023-01-01', server='http://example.com')
        )
    args = argparse.ArgumentParser.parse_args()
    _adapter.register_uri(
        'GET', f"{args.server}/{drupalApi.node_view_endpoint(page='0', date_filter=args.date)}",
        text = '[ { "nid" : [{"value": 1}], "changed" : [{"value": "2024-01-01"}] } ]'
        )
    _adapter.register_uri(
        'GET', f"{args.server}/{drupalApi.node_view_endpoint(page='1', date_filter=args.date)}",
        text = '[]'
        )
    _adapter.register_uri(
        'GET', f"{args.server}/{drupalApi.media_view_endpoint(page='0', date_filter=args.date)}",
        text = '[ { "changed": [{"value": "2025-01-01"}], "field_media_of": [{"target_id": 1}] } ]'
        )
    _adapter.register_uri(
        'GET', f"{args.server}/{drupalApi.media_view_endpoint(page='1', date_filter=args.date)}",
        text = '[]'
        )
    node_list = drupalUtilities.id_list_from_nodes(_session, args)
    drupalUtilities.id_list_merge_with_media(_session, args, node_list)
    assert node_list[1]
    assert node_list[1]['changed'] == '2025-01-01'
