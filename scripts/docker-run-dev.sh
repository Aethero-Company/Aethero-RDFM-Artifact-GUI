#!/bin/bash
# RDFM Artifact Tool - Docker Launcher
# Launch the standalone RDFM Artifact creation GUI

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

# Allow X11 connections from docker
if command -v xhost &>/dev/null; then
    xhost +local:docker &>/dev/null || true
fi

echo "Starting RDFM Artifact Tool..."
echo "Home mounted at: /home/$CONTAINER_USER"
echo "Working directory: $CONTAINER_WORKDIR"

# Check if Docker socket exists for docker save functionality
DOCKER_SOCKET_MOUNT=""
DOCKER_GROUP_ADD=""
if [[ -S /var/run/docker.sock ]]; then
    DOCKER_SOCKET_MOUNT="-v /var/run/docker.sock:/var/run/docker.sock"
    # Get the GID of the docker socket to grant access in container
    DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)
    DOCKER_GROUP_ADD="--group-add $DOCKER_GID"
    echo "Docker socket: mounted (docker save enabled)"
else
    echo "Docker socket: not available (use existing tarballs for Docker artifacts)"
fi
echo ""

docker run --rm -it \
    --name rdfm-artifact-gui \
    -e DISPLAY="$DISPLAY" \
    -e XAUTHORITY=/tmp/.Xauthority \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v "${XAUTHORITY:-$HOME/.Xauthority}:/tmp/.Xauthority:ro" \
    -v "$HOME:/home/$CONTAINER_USER" \
    -v ./app/:/app/app/ \
    -v ./pyproject.toml:/app/pyproject.toml:ro \
    $DOCKER_SOCKET_MOUNT \
    $DOCKER_GROUP_ADD \
    -w "$CONTAINER_WORKDIR" \
    --network host \
    aethero/rdfm-artifact-gui \
    bash -c "PYTHONPATH=/app python3 -m app.artifact_tool"