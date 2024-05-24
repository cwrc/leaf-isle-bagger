# syntax=docker/dockerfile:1.7
ARG BAGGER_REPOSITORY
ARG BAGGER_TAG

FROM --platform=$BUILDPLATFORM ${BAGGER_REPOSITORY:-ghcr.io/cwrc}/isle-bagger:${BAGGER_TAG:-v0.0.1}

# Install packages and tools that allow for basic downloads.
RUN --mount=type=cache,id=bagger-apk-${TARGETARCH},sharing=locked,target=/var/cache/apk \
    apk add --no-cache \
        python3 \
        py-pip \
        py3-requests \
    && \
    echo '' > /root/.ash_history

WORKDIR /var/www/

# requries v24+ of Docker
# https://github.com/docker/build-push-action/issues/761
#COPY --chown=nginx:nginx --link rootfs /
COPY --chown=nginx:nginx rootfs/ /var/www/

WORKDIR /var/www/leaf-isle-bagger

# Install non-apk python packages in a virtual environment
# Avoid "This environment is externally managed" error in not in a virtual environment
# hint: See PEP 668 for the detailed specification.
RUN \
    python3 -m venv ./venv/ \
    && \
    ./venv/bin/python3 -m pip install -r requirements.txt 
