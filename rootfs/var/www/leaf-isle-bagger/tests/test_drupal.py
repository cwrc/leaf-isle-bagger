"""
Test the Drupal integration module
"""

import argparse
import os
import requests
import requests_mock
import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)  # noqa:E402

from drupal import utilities as drupalUtilities  # noqa:E402
from drupal import api as drupalApi  # noqa:E402

# Mock pages of request responses
# https://github.com/jamielennox/requests-mock/tree/master
_session = requests.Session()
_adapter = requests_mock.Adapter()
_session.mount("http://", _adapter)


# Test Drupal node change view reader
def test_drupal_node_change_view(mocker):
    # doesn't work with multiple pages
    # mock_response_page_1 = mocker.MagicMock()
    # mock_response_page_1.configure_mock(
    #    **{
    #        'content': '[ { "nid" : [{"value":1}], "changed" : [{"value": "2024-01-01"}] } ]'
    #    }
    # )
    # mock_response_page_2 = mocker.MagicMock()
    # mock_response_page_2.configure_mock(
    #    **{
    #        'content': '[]'
    #    }
    # )
    # mocker.patch(
    #    'leaf-bagger.drupalApi.get_node_list',
    #    return_value=mock_response
    #    )
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(date="2023-01-01", server="http://example.com"),
    )
    args = argparse.ArgumentParser.parse_args()
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.node_view_endpoint(page='0', date_filter=args.date)}",
        text='[ { "nid" : "1", "changed" : "1704067200" } ]',
    )
    # Test both English and French translations that yeilds 2 nodes in the view with the same ID
    # use the lates one
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.node_view_endpoint(page='1', date_filter=args.date)}",
        text='[ { "nid" : "1", "changed" : "1604067200" } ]',
    )
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.node_view_endpoint(page='2', date_filter=args.date)}",
        text="[]",
    )
    node_list = drupalUtilities.id_list_from_nodes(_session, args)
    assert node_list["1"]
    assert node_list["1"]["changed"] == "2024-01-01T00:00:00+00:00"


# Test the Drupal media change view reader
def test_drupal_media_change_view(mocker):
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(date="2023-01-01", server="http://example.com"),
    )
    args = argparse.ArgumentParser.parse_args()
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.media_view_endpoint(page='0', date_filter=args.date)}",
        text='[ { "changed": "1735689600", "field_media_of": "1" } ]',
    )
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.media_view_endpoint(page='1', date_filter=args.date)}",
        text="[]",
    )
    node_list = {}
    print(node_list)
    drupalUtilities.id_list_merge_with_media(_session, args, node_list)
    print(node_list)
    assert node_list["1"]
    assert node_list["1"]["changed"] == "2025-01-01T00:00:00+00:00"


# When media is updated the associated node is not updated;
# test that the date list captures the media date not the node date
def test_drupal_media_change_without_node(mocker):
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(date="2023-01-01", server="http://example.com"),
    )
    args = argparse.ArgumentParser.parse_args()
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.node_view_endpoint(page='0', date_filter=args.date)}",
        text='[ { "nid" : "1", "changed" : "1704067200" } ]',
    )
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.node_view_endpoint(page='1', date_filter=args.date)}",
        text="[]",
    )
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.media_view_endpoint(page='0', date_filter=args.date)}",
        text='[ { "changed": "1735689600", "field_media_of": "1" } ]',
    )
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.media_view_endpoint(page='1', date_filter=args.date)}",
        text="[]",
    )
    node_list = drupalUtilities.id_list_from_nodes(_session, args)
    drupalUtilities.id_list_merge_with_media(_session, args, node_list)
    assert node_list["1"]
    assert node_list["1"]["changed"] == "2025-01-01T00:00:00+00:00"


# When node is updated the associated media is not updated;
# test that the date list captures the media date not the node date
def test_drupal_node_change_without_media(mocker):
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(date="2023-01-01", server="http://example.com"),
    )
    args = argparse.ArgumentParser.parse_args()
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.node_view_endpoint(page='0', date_filter=args.date)}",
        text='[ { "nid" : "1", "changed" : "1735776000" } ]',
    )
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.node_view_endpoint(page='1', date_filter=args.date)}",
        text="[]",
    )
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.media_view_endpoint(page='0', date_filter=args.date)}",
        text='[ { "changed": "1704067200", "field_media_of": "1" } ]',
    )
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.media_view_endpoint(page='1', date_filter=args.date)}",
        text="[]",
    )
    node_list = drupalUtilities.id_list_from_nodes(_session, args)
    drupalUtilities.id_list_merge_with_media(_session, args, node_list)
    assert node_list["1"]
    assert node_list["1"]["changed"] == "2025-01-02T00:00:00+00:00"


# Test the update of a single node with associated media
# test that the date list captures the media date not the node date
def test_single_drupal_node_change_without_media(mocker):
    node_id = 9999
    node_list = {
        9999: {
            "changed": "2022-05-18T13:35:49+00:00",
            "content_type": "application/zip",
        }
    }
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(
            force_single_node=node_id, server="http://example.com"
        ),
    )
    args = argparse.ArgumentParser.parse_args()
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.media_associated_with_node_endpoint(node_id)}",
        text='[ { "changed": [{"value": "2022-05-18T13:35:52+00:00"}], "field_media_of": [{"target_id": 9999}] } ]',
    )
    drupalUtilities.single_node_merge_with_media(
        _session, args.server, node_list, args.force_single_node
    )
    assert node_list[node_id]
    assert node_list[node_id]["changed"] == "2022-05-18T13:35:52+00:00"


# Test Drupal Group update inclusion
def test_drupal_group_change_date():
    date_gr = drupalUtilities.get_changed_date(
        {
            "group_changed_on": "1758126493",
            "group_relationship_changed_on": "1774280464",
        }
    )
    date_g = drupalUtilities.get_changed_date(
        {
            "group_changed_on": "1774280464",
            "group_relationship_changed_on": "1758126493",
        }
    )
    date_gr_none = drupalUtilities.get_changed_date(
        {
            "group_changed_on": "1774280464",
            "group_relationship_changed_on": "",
        }
    )
    date_g_none = drupalUtilities.get_changed_date(
        {
            "group_changed_on": "",
            "group_relationship_changed_on": "1758126493",
        }
    )
    assert date_gr == "2026-03-23T15:41:04+00:00"
    assert date_g == "2026-03-23T15:41:04+00:00"
    assert date_gr_none == "2026-03-23T15:41:04+00:00"
    assert date_g_none == "2025-09-17T16:28:13+00:00"


# Test Drupal Group change view
def test_drupal_group_change(mocker):
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(date="2023-01-01", server="http://example.com"),
    )
    args = argparse.ArgumentParser.parse_args()
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.group_view_endpoint(page='0', date_filter=args.date)}",
        text='[ { "group_changed_on": "1758126493", "group_relationship_changed_on": "1774280464",'
        ' "node_id": "1" } ]',
    )
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.group_view_endpoint(page='1', date_filter=args.date)}",
        text="[]",
    )
    node_list = {"1": {"changed": "2024-01-01T00:00:00+00:00"}}
    drupalUtilities.id_list_merge_with_drupal_groups(_session, args, node_list)
    assert node_list["1"]
    assert node_list["1"]["changed"] == "2026-03-23T15:41:04+00:00"


# Test the update of a single node with associated media
# test that the date list captures the media date not the node date
def test_single_drupal_node_change_with_recent_group_change_date(mocker):
    node_id = 9999
    node_list = {
        9999: {
            "changed": "2022-05-18T13:35:49+00:00",
            "content_type": "application/zip",
        }
    }
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(
            force_single_node=node_id, date="2023-01-01", server="http://example.com"
        ),
    )
    args = argparse.ArgumentParser.parse_args()
    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.media_associated_with_node_endpoint(node_id)}",
        text='[ { "changed": [{"value": "2022-05-18T13:35:52+00:00"}], "field_media_of": [{"target_id": 9999}] } ]',
    )
    drupalUtilities.single_node_merge_with_media(
        _session, args.server, node_list, args.force_single_node
    )

    _adapter.register_uri(
        "GET",
        f"{args.server}/{drupalApi.group_node_view_endpoint(node_id)}",
        text='[ { "group_changed_on": "1758126493", "group_relationship_changed_on": "1774280464",'
        ' "field_group_of": "1" } ]',
    )
    drupalUtilities.single_node_merge_with_drupal_group(
        _session, args.server, node_list, args.force_single_node
    )
    assert node_list[node_id]
    assert node_list[node_id]["changed"] == "2026-03-23T15:41:04+00:00"
