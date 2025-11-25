#!/bin/bash
# RDFM Artifact CLI - Docker Launcher
# Run rdfm-artifact commands directly
# Usage: rdfm-artifact-cli [args...]
# Example: rdfm-artifact-cli write rootfs-image -t my-artifact -n "Test" -o output.rdfm rootfs.ext4

set -e

# Container user matches host user (set during docker build)
CONTAINER_USER="$(whoami)"

# Calculate container working directory (map current dir under container home)
if [[ "$PWD" == "$HOME" ]]; then
    CONTAINER_WORKDIR="/home/$CONTAINER_USER"
elif [[ "$PWD" == "$HOME/"* ]]; then
    CONTAINER_WORKDIR="/home/$CONTAINER_USER/${PWD#$HOME/}"
else
    # PWD is not under HOME, fall back to container home
    CONTAINER_WORKDIR="/home/$CONTAINER_USER"
fi

docker run --rm -it \
    --name rdfm-artifact-run \
    -v "$HOME:/home/$CONTAINER_USER" \
    -w "$CONTAINER_WORKDIR" \
    --network host \
    aethero/rdfm-artifact-gui \
    rdfm-artifact "$@"