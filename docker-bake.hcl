variable "ISLE_BAGGER_REGISTRY" {
    default = "ghcr.io/cwrc"
    }
variable "ISLE_BAGGER_VERSION" {
    default = "v0.0.9@sha256:32cec9b7e93601e73bf74a02d2706fef0771c975b5903753e79860a44e6078ab"
    }

###############################################################################
# Common target properties.
###############################################################################
target "common" {
  args = {
    # Required for reproduciable builds.
    # Requires Buildkit 0.11+
    # See: https://reproducible-builds.org/docs/source-date-epoch/
    # SOURCE_DATE_EPOCH = "${SOURCE_DATE_EPOCH}",
  }
}

# https://github.com/docker/metadata-action?tab=readme-ov-file#bake-definition
# bake definition file that can be used with the Docker Bake action. You just
# have to declare an empty target named docker-metadata-action and inherit from it.
target "docker-metadata-action" {}

###############################################################################
# Groups
###############################################################################

group "default" {
  targets = ["leaf-bagger"]
}

###############################################################################
# Target.
###############################################################################
# The digest (sha256 hash) is not platform specific but the digest for the manifest of all platforms.
# It will be the digest printed when you do: docker pull alpine:3.17.1
# Not the one displayed on DockerHub.

target "leaf-bagger" {
  inherits = ["common", "docker-metadata-action"]
  dockerfile = "Dockerfile"
  contexts = {
    isle_bagger = "docker-image://${ISLE_BAGGER_REGISTRY}/isle-bagger:${ISLE_BAGGER_VERSION}"
    #isle_bagger = "docker-image://ISLE_BAGGER_REGISTRY}/drupal:${ISLE_BAGGER_VERSION}"
    #BAGGER_TAG = "v0.0.5@sha256:4e05219adb36595ddfc51fee33a35ead45fced6b01f57e157bcc01d2608a4aae"
  }
}
