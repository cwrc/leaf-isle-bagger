# leaf-isle-bagger

Create Archival Information Packages (AIP) from the LEAF environment

## Requirements

* Assumes a Drupal instance with the following required Drupal Views REST endpoints
  * `views/preservation_show_node_timestamps?page={page}&changed={date_filter}`
  * `views/preservation_show_media_timestamps?page={page}&changed={date_filter}`
* An instance of Islandora-Bagger CLI
  * directory of to store generated AIPs (long-term for auditing)
* A shell with OpenStack Swift environment variables
* PHP 8.3+ for Islandora-Bagger
* Python3

``` bash
./rootfs/leaf-isle-bagger/venv/bin/python3 -m pip install -r rootfs/leaf-isle-bagger/requirements.txt`
```

## Workflow: Archival Package Creation

* Creates a subset of Drupal Nodes IDs filtered on Drupal Node change date (or associated Drupal Media change date, i.e., if the attached Drupal Media changes the Node change date will not change)
* For each item in the list, build an archival information package (AIP) via the `islandora-bagger` tool
* Upload AIP to an OpenStack Swift instance
* Run a post upload validation

## Workflow: Archival Package Audit

* test node list id and timestamps

`leaf-bagger-audit.py`

* test the Drupal changed date against
  * filesystem AIP
  * OLRC AIP
* test the checksum: filesystem versus OLRC

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
