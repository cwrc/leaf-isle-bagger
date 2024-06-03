# LEAF Bagger

Supports a preservation workflow through the creation of Archival Information Packages (AIP) from a [LEAF](https://gitlab.com/calincs/cwrc/leaf/leaf-base-i8) environment.

> :warning: **These command-line scripts are only compatible with CWRC Repository v2.0** based on [Linked Academic Editing Framework (LEAF)](https://gitlab.com/calincs/cwrc/leaf/leaf-base-i8). This replaces preservation workflow: [cwrc_preservation](https://github.com/ualbertalib/cwrc_preservation) used with the [CWRC Repository v1.0](https://github.com/cwrc/beta.cwrc.ca) as v1.0 reached end-of-life Jan 5th, 2025.

## Overview

The LEAF Bagger preservation toolkit contains scripts supporting a preservation workflow for a LEAF environment. The primary objective is to manage the flow of content from the CWRC repository into an OpenStack Swift repository for preservation (the destination may be extended for partner projects). Also, the repository provides an application to audit the contents of the source and preserved objects. The scripts are deployable within an OCI container to align with the deployment of CWRC Repository v2.0 and other LEAF installations.

## What is CWRC

[CWRC (Canadian Writing Research Collaboratory)](https://cwrc.ca/about) is an “online infrastructure for literary research in and about Canada designed to meet the challenges and embrace the opportunities of the digital turn.” In other words, CWRC is a living repository (i.e., contains content that may be updated, for example, as facts and assertions about a person, place, or event are discovered or changed). CWRC, as of August 2023, contains ~410,000 objects accounting for 1TB+ in storage. The content comes from multiple research projects created by researchers located in many areas of Canada.

CWRC infrastructure is hosted with the Digital Research Alliance of Canada on the [Arbutus](https://docs.alliancecan.ca/wiki/Cloud_resources) Cloud hosted at the University of Victoria with data backups hosted in London ON and preservation with UofA Library (via [OLRC](https://cloud.scholarsportal.info/)).

## Requirements

The Dockerfile in this repository describes the requirements and setup. An overview of requirements includes:

- Assumes a Drupal instance with the following required [Drupal Views REST endpoints](https://gitlab.com/calincs/cwrc/leaf/leaf-base-i8/-/merge_requests/200)
  - `views/preservation_show_node_timestamps?page={page}&changed={date_filter}`
  - `views/preservation_show_media_timestamps?page={page}&changed={date_filter}`
- An instance of [Islandora-Bagger CLI](https://github.com/mjordan/islandora_bagger) via [isle-bagger](https://github.com/cwrc/isle-bagger) or an equivalent setup
  - directory of to store generated AIPs (long-term for auditing)
  - [jwtonlogin] (to add the user's JWT token to the response of a successful login)
  - See [isle-bagger] for details
- A shell with OpenStack Swift environment variables
- PHP 8.3+ for Islandora-Bagger
- Python 3.10
- leaf-isle-bagger/requirements.txt`

## Workflow: Archival Package Creation

The preservation workflow acts on a polling model where a script runs at regular intervals asking the repository for a list of new/changed items within a given window of time. Any new/changed item has an archival information package generated (AIP) and added to the preservation endpoint.

`leaf-bagger.py`

- REST request to the site for a list of nodes filtered by change date (or media change date, i.e., if the attached Drupal Media changes the Drupal Node change date will not change)
- For each item in the list, build an archival information package (AIP) via the [islandora-bagger] CLI tool and store the generated AIP locally
  - More information on the tool:
    - [islandora-bagger]
    - [isle-bagger]
- Upload AIP to an OpenStack Swift instance
- Run a post-upload validation

Result: a report of items added to the preservation endpoint.

### How to recover from isolated failures

**ToDo:** what if a small percentage of items in a preservation run fail?

- option 1.: enhancement: script CLI argument specifying a list of item IDs to preserve thus overriding the REST request to the repository
- option 2.: enhancement: only generate AIP and upload if the preservation endpoint is missing the item or is stale/outdated
- option 3.: run the [islandora-bagger] CLI outside the scripting (downside: loss of the report)
  - from within the container: `cd ${BAGGER_APP_DIR} && ./bin/console app:islandora_bagger:create_bag -vvv --settings=var/sample_per_bag_config.yaml --node=${drupal_node_id}`

## Workflow: Archival Package Audit

The preservation workflow includes an audit step checking, in a basic way, that what exists in the repository is preserved in the preservation endpoint. This step assumes the AIP creation script will fail in unexpected ways and tries to act as a second set of eyes to identify and report failures.

`leaf-bagger-audit.py`

- REST request to the site for a list of all nodes (and their change date, either from the node or attached media whichever is more recent, i.e., if the attached Drupal Media changes the Drupal Node change date will not change)
- Test against the locally stored AIP for presence and timestamp
- Test against the Swift collection for presence, timestamps, and checksums (locally stored AIP and Swift objects)

Result: an audit report indicating the status of all nodes in the repository and their preservation status in a CSV file.

## Tests & linting

The [Nox](https://nox.thea.codes/en/stable/index.html) Python automation tooling helps automate testing and linting. The tool is integrated as part of the CI/CD. The `noxfile.py` contains the configuration.

Install as per your OS, e.g., `apt install nox`

To run tests and linting:

> nox

To run only tests

> nox -s test

To run only linting

> nox -s lint

To run tests outside `nox`

- setup virtual environment

```bash
python3 -m venv ./rootfs/leaf-isle-bagger/venv
./rootfs/leaf-isle-bagger/venv/bin/python3 -m pip install -r rootfs/leaf-isle-bagger/requirements.txt
./rootfs/leaf-isle-bagger/venv/bin/python3 -m pip install -r rootfs/leaf-isle-bagger/requirements_test.txt
```

- run tests within the virtual environment

```bash
./rootfs/leaf-isle-bagger/venv/bin/pytest rootfs/leaf-isle-bagger/tests/
```

## CI/CD

- Run tests and code linting on each code push
- Build an OCI container to host the preservation workflow tooling and automate execution
- Future: automate deployment

## Deployment

The scripts are meant to be executed within a containerized environment. For alternate approaches, review the Dockerfile layers for installation and docker-compose.yml for environment variable settings.

### How to run from within a container

- `docker compose exec bagger with-contenv bash`
- `su -s /bin/bash nginx -c "./venv/bin/python3 leaf-bagger.py --server ${BAGGER_DRUPAL_URL} --output /tmp/z.csv --force_single_node 1 --container cwrc-test"`
- see `rootfs/etc/s6-overlay/scripts/bagger-setup.sh` for an example of both leaf-bagger.py and leaf-bagger-audit.py

### Dependencies

The OCI container image is based on the [isle-bagger] image and [isle-buildkit]. Access to a Drupal site is also required with the container running within a [leaf-base-i8] container deployment or independently (i.e., in a separate deployment).

### Settings

Local settings: see [isle-bagger] and parent containers for more settings (e.g., [islandora-bagger] tool settings). [.env.sample](.env.sample) contains a sample `.env` for docker-compose

| Environment Variable          | Default                    | Description                                                   |
| :---------------------------- | :------------------------- | :------------------------------------------------------------ |
| LEAF_BAGGER_APP_DIR           | /var/www/leaf-isle-bagger/ | The installed directory of [islandora-bagger]                 |
| LEAF_BAGGER_OUTPUT_DIR        | /data/log/                 | Report location describing AIP creation & upload              |
| LEAF_BAGGER_AUDIT_OUTPUT_DIR  | /data/log/                 | Audit report location                                         |
| LEAF_BAGGER_CROND_DATE_WINDOW | 86400                      | Time window; return new/changed items in the last "x" seconds |
| OS_CONTAINER                  |                            | OpenStack container name                                      |
| OS_AUTH_URL                   |                            | OpenStack auth URL                                            |
| OS_PROJECT_ID                 |                            | OpenStack project ID                                          |
| OS_PROJECT_NAME               |                            | OpenStack project name                                        |
| OS_USER_DOMAIN_NAME           |                            | OpenStack user domain name                                    |
| OS_PROJECT_DOMAIN_ID          |                            | OpenStack project domain id                                   |
| OS_USERNAME                   |                            | OpenStack user name                                           |
| OS_REGION_NAME                |                            | OpenStack region name                                         |
| OS_INTERFACE                  |                            | OpenStack interface                                           |
| OS_IDENTITY_API_VERSION       |                            | OpenStack identity API version                                |

Two docker-compose secrets are also used

| Secret                                 | Description             |
| :------------------------------------- | :---------------------- |
| BAGGER_DRUPAL_DEFAULT_ACCOUNT_PASSWORD | Drupal site password    |
| OS_PASSWORD                            | OpenStack user password |

Docker-compose env vars

| Environment Variable   | Default      | Description                                                                        |
| :--------------------- | :----------- | :--------------------------------------------------------------------------------- |
| LOCAL_AIP_DIR          |              | Set when using a bind mount; otherwise a Docker volume                             |
| LEAF_BAGGER_REPOSITORY | ghcr.io/cwrc | IOC image repository for the LEAF Bagger image; defaults to a local build          |
| LEAF_BAGGER_TAG        | latest       | IOC image tag name for the LEAF Bagger image; defaults to latest for a local build |
| BAGGER_REPOSITORY      | ghcr.io/cwrc | IOC image repository for the Isle Bagger image; defaults to a local build          |
| BAGGER_TAG             | latest       | IOC image tag name for the Isle Bagger image; defaults to latest for a local build |

## Updates

How to update the base?

For an [isle-buildkit] update (gist, follow dependencies in the Dockerfile layers)

- update [isle-bagger] (Dockerfile or [bake file](https://docs.docker.com/build/bake/reference/)) with the new [isle-buildkit] TAG
  - create a new tag release
- update [leaf-isle-bagger] (Dockerfile or [bake file](https://docs.docker.com/build/bake/reference/)) with the [isle-bagger] TAG
  - create a new tag release
- update the new [leaf-isle-bagger] OCI image TAG in the production deployment

Note: if wanting to test [leaf-isle-bagger] and [isle-bagger] locally

- update the [isle-bagger] .env with the ISLE_TAG and `docker compose build`
  - this creates a locally stored image with the TAG set in the .env
- `docker compose build` [leaf-isle-bagger] using the same TAG for [isle-bagger] as in the previous step
  - this creates a locally stored image with the TAG set in the .env
- `docker compose up -d` to run the container
- `docker compose exec bagger with-contenv bash` to shell into the container

See the following as an alternative to specifying an OCI image registry and tag in the Dockerfile: <https://docs.docker.com/build/bake/reference/>. As an example, see [isle-buildkit] `docker-bake.hcl`.

---

[isle-bagger]: https://github.com/cwrc/isle-bagger
[isle-buildkit]: https://github.com/islandora-Devops/isle-buildkit
[islandora-bagger]: https://github.com/mjordan/islandora-bagger
[leaf-isle-bagger]: https://github.com/cwrc/leaf-isle-bagger
[jwtonlogin]: https://www.drupal.org/project/getjwtonlogin
