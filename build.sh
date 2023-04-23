#!/usr/bin/env bash

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

podman build --no-cache --tag "${IMAGE_FQN}" .

podman push "${IMAGE_FQN}"

