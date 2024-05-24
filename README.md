# leaf-isle-bagger

Create Archival Information Packages (AIP) from the LEAF environment

## Steps

* Assumes Drupal endpoint with two required Drupal Views
  * `views/preservation_show_node_timestamps?page={page}&changed={date_filter}`
  * `views/preservation_show_media_timestamps?page={page}&changed={date_filter}`
* Creates a subset of Drupal Nodes IDs filtered on Drupal Node change date (or associated Drupal Media change date, i.e., if the attached Drupal Media changes the Node change date will not change)
* For each item in the list, build an archival information package (AIP) via the `islandora-bagger` tool
* Upload AIP to an OpenStack Swift instance

## Test

Test within a virtual environment

* setup virtual environment

``` bash
python3 -m venv ./rootfs/leaf-isle-bagger/venv
./rootfs/leaf-isle-bagger/venv/bin/python3 -m pip install -r rootfs/leaf-isle-bagger/requirements.txt
./rootfs/leaf-isle-bagger/venv/bin/python3 -m pip install -r rootfs/leaf-isle-bagger/requirements_test.txt
```

* run tests

``` bash
./rootfs/leaf-isle-bagger/venv/bin/pytest rootfs/leaf-isle-bagger/tests/
```
