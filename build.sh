#!/usr/bin/env bash

SCRIPT_HOME="$(dirname $(readlink -f $0))"

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

podman build --no-cache --tag "${IMAGE_FQN}" "${SCRIPT_HOME}"
RTN=$?
if [ $RTN -ne 0 ]
then
    echo "Building ${IMAGE_FQN} failed ..."
    exit $RTN
fi

podman push "${IMAGE_FQN}"

