#!/usr/bin/env bash

SCRIPT_HOME="$(dirname "$(readlink -f "$0")")"
IMAGE_PLATFORM="linux/amd64"

function clean_up()
{
    echo "Cleanup ..."
    podman image prune --force
}

trap clean_up EXIT

IMAGE_FQN="$1"
if [ -z "${IMAGE_FQN}" ]
then
    echo "ERROR: Image name and tag missing!"
    exit 1
fi

echo "Building ${IMAGE_FQN} ..."
podman build --platform=${IMAGE_PLATFORM} \
       --pull=always --no-cache --tag "${IMAGE_FQN}" "${SCRIPT_HOME}"
RTN=$?
if [ $RTN -ne 0 ]
then
    echo "Building ${IMAGE_FQN} failed ..."
    exit $RTN
fi

echo
echo "Pushing ${IMAGE_FQN} to registry ..."
podman push "${IMAGE_FQN}"
RTN=$?
if [ $RTN -ne 0 ]
then
    echo "Pushing ${IMAGE_FQN} failed ..."
    exit $RTN
fi

