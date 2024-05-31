# syntax=docker/dockerfile:1.7
ARG BAGGER_REPOSITORY
ARG BAGGER_TAG

# ---------------------------
# Base build layer
# ---------------------------
FROM --platform=$BUILDPLATFORM ${BAGGER_REPOSITORY:-ghcr.io/cwrc}/isle-bagger:${BAGGER_TAG:-v0.0.3} as base

# Install packages and tools that allow for basic python install.
# python-keystoneclient requirements
#   gcc \
#   libc-dev \
#   linux-headers \
#   python3-dev \
RUN --mount=type=cache,id=bagger-apk-${TARGETARCH},sharing=locked,target=/var/cache/apk \
    apk add --no-cache \
        gcc \
        libc-dev \
        linux-headers \
        python3-dev \
        python3 \
        py-pip \
        py3-requests \
    && \
    echo '' > /root/.ash_history

WORKDIR /var/www/

# requries v24+ of Docker
# https://github.com/docker/build-push-action/issues/761
#COPY --chown=nginx:nginx --link rootfs /
COPY --chown=nginx:nginx rootfs/var/www/leaf-isle-bagger/requirements/requirements.txt /var/www/leaf-isle-bagger/requirements/requirements.txt

WORKDIR /var/www/leaf-isle-bagger

# Install non-apk python packages in a virtual environment
# Avoid "This environment is externally managed" error in not in a virtual environment
# hint: See PEP 668 for the detailed specification.
# Requires python-keystoneclient
RUN \
    python3 -m venv ./venv/ \
    && \
    ./venv/bin/python3 -m pip install -r requirements/requirements.txt 

# ---------------------------
# Production layer
# ---------------------------

FROM --platform=$BUILDPLATFORM ${BAGGER_REPOSITORY:-ghcr.io/cwrc}/isle-bagger:${BAGGER_TAG:-v0.0.2} as prod

# Install packages and tools that allow for basic downloads.
# cleanup unused base image components
RUN --mount=type=cache,id=bagger-apk-${TARGETARCH},sharing=locked,target=/var/cache/apk \
    apk add --no-cache \
        python3 \
        py3-requests \
    && \
    rm -rf /etc/s6-overlay/s6-rc.d/user/contents.d/fpm /etc/s6-overlay/s6-rc.d/user/contents.d/nginx \
    && \
    rm -rf /etc/s6-overlay/s6-rc.d/nginx* /etc/s6-overlay/s6-rc.d/fpm* \
    && \
    echo '' > /root/.ash_history

WORKDIR /var/www/leaf-isle-bagger


COPY --chown=nginx:nginx rootfs/ /
COPY --chown=nginx:nginx --from=base /var/www/leaf-isle-bagger/venv /var/www/leaf-isle-bagger/venv

ENV \
    LEAF_BAGGER_APP_DIR=/var/www/leaf-isle-bagger/ \
    LEAF_BAGGER_OUTPUT_DIR=/data/log/ \
    LEAF_BAGGER_AUDIT_OUTPUT_DIR=/data/log/ \
    LEAF_BAGGER_CROND_DATE_WINDOW=86400 \
    OS_CONTAINER= \
    OS_AUTH_URL= \
    OS_PROJECT_ID= \
    OS_PROJECT_NAME= \
    OS_USER_DOMAIN_NAME= \
    OS_PROJECT_DOMAIN_ID= \
    OS_USERNAME= \
    OS_REGION_NAME= \
    OS_INTERFACE= \
    OS_IDENTITY_API_VERSION=
