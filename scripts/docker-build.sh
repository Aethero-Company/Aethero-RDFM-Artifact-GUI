#!/bin/bash
# Build the RDFM GUI Docker image
# Usage: ./scripts/docker-build.sh [--no-cache]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Building RDFM GUI Docker image..."

# Build arguments (UID/GID/username for user permission mirroring)
BUILD_ARGS=(
    --build-arg "UNAME=$(whoami)"
    --build-arg "UID=$(id -u)"
    --build-arg "GID=$(id -g)"
    --build-arg "RDFM_REV=c36e6a9072cf2f0a2b05c75a0a67f9040f1e9243"
)

# Add --no-cache if requested
if [[ "$1" == "--no-cache" ]]; then
    BUILD_ARGS+=(--no-cache)
    echo "Building without cache..."
fi

# Build with buildx for better caching
if docker buildx version &>/dev/null; then
    docker buildx build \
        --load \
        "${BUILD_ARGS[@]}" \
        -t aethero/rdfm-artifact-gui \
        .
else
    docker build \
        "${BUILD_ARGS[@]}" \
        -t aethero/rdfm-artifact-gui \
        .
fi

echo ""
echo "Build complete! Image: aethero/rdfm-artifact-gui"
