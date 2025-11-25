#!/bin/bash
#
# RDFM GUI Unified Installation Script
#
# This script provides a unified interface for installing RDFM tools
# using either Docker or native installation.
#
# By default, only rdfm-artifact and the artifact GUI are installed.
# Use --full to install the complete rdfm-mgmt interface.
#
# Usage:
#   ./scripts/install.sh docker [OPTIONS]  - Install using Docker
#   ./scripts/install.sh native [OPTIONS]  - Install natively (requires build tools)
#
# Docker installation options:
#   --full                    Install full suite including rdfm-mgmt GUI
#   -e, --cli-exports <tool>  Also install CLI tool wrappers (can specify multiple)
#                             Valid values: artifact, mgmt
#
# Docker installation:
#   - Builds the Docker image
#   - Creates launcher script in ~/.local/bin (rdfm-artifact-gui)
#   - With --full: also creates rdfm-gui launcher
#   - Optionally creates CLI wrappers (rdfm-mgmt-cli, rdfm-artifact-cli)
#   - Adds ~/.local/bin to PATH if needed
#
# Native installation:
#   - Installs system dependencies
#   - Builds and installs rdfm-artifact and rdfm-gui
#   - With --full: also installs rdfm-mgmt
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine script and project directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Installation directory for launcher scripts
INSTALL_DIR="$HOME/.local/bin"

# Installation options
NO_CACHE=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show usage information
show_usage() {
    echo "Usage: $0 <docker|native> [OPTIONS]"
    echo ""
    echo "Installation methods:"
    echo "  docker    Install using Docker containers"
    echo "  native    Install natively on the system"
    echo ""
    echo "Options for Docker installation:"
    echo "  --no-cache         Build the docker container without using the build cache"
    echo ""
    echo "Options for native installation:"
    echo "  --skip-gui         Skip installing rdfm-gui"
    echo "  --skip-deps        Skip installing system dependencies"
    echo "  --help             Show this help message"
    exit 1
}

# Create the rdfm-artifact-gui launcher script for Docker
create_rdfm_artifact_gui_script() {
    log_info "Creating rdfm-artifact-gui launcher script..."

    cp "$SCRIPT_DIR/docker-run-artifact-gui.sh" "$INSTALL_DIR/rdfm-artifact-gui"

    chmod +x "$INSTALL_DIR/rdfm-artifact-gui"
    log_success "Created $INSTALL_DIR/rdfm-artifact-gui"
}

# Create the rdfm-artifact-cli launcher script for Docker
create_rdfm_artifact_cli_script() {
    log_info "Creating rdfm-artifact-cli launcher script..."

    cp "$SCRIPT_DIR/docker-run-artifact.sh" "$INSTALL_DIR/rdfm-artifact"

    chmod +x "$INSTALL_DIR/rdfm-artifact"
    log_success "Created $INSTALL_DIR/rdfm-artifact"
}

# Add ~/.local/bin to PATH in shell configuration
add_to_path() {
    # Check if already in PATH
    if [[ ":$PATH:" == *":$INSTALL_DIR:"* ]]; then
        log_info "$INSTALL_DIR is already in PATH"
        return
    fi

    log_info "Adding $INSTALL_DIR to PATH..."

    # Detect user's shell
    CURRENT_SHELL=$(basename "$SHELL")

    case "$CURRENT_SHELL" in
        zsh)
            SHELL_RC="$HOME/.zshrc"
            ;;
        fish)
            # Fish uses a different syntax
            SHELL_RC="$HOME/.config/fish/config.fish"
            mkdir -p "$(dirname "$SHELL_RC")"
            if ! grep -q "set -gx PATH.*$INSTALL_DIR" "$SHELL_RC" 2>/dev/null; then
                echo "set -gx PATH \"$INSTALL_DIR\" \$PATH" >> "$SHELL_RC"
                log_success "Added to $SHELL_RC"
            fi
            return
            ;;
        *)
            SHELL_RC="$HOME/.bashrc"
            ;;
    esac

    # Add to shell configuration if not already present
    if ! grep -q "export PATH=.*$INSTALL_DIR" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Added by RDFM GUI installer" >> "$SHELL_RC"
        echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$SHELL_RC"
        log_success "Added to $SHELL_RC"
    else
        log_info "PATH export already exists in $SHELL_RC"
    fi
}

# Docker installation
install_docker() {
    echo ""
    echo "======================================"
    echo "RDFM Artifact Tool Docker Installation"
    echo "======================================"
    echo ""

    # Check for Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        log_info "See: https://docs.docker.com/get-docker/"
        exit 1
    fi

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi

    # Build Docker image
    log_info "Building Docker image..."
    if (( NO_CACHE )); then
        if ! "$SCRIPT_DIR/docker-build.sh" --no-cache; then
            log_error "Failed to build Docker image"
            exit 1
        fi
    else
        if ! "$SCRIPT_DIR/docker-build.sh"; then
            log_error "Failed to build Docker image"
            exit 1
        fi
    fi

    # Create installation directory
    mkdir -p "$INSTALL_DIR"

    # Create artifact GUI launcher script (always installed)
    create_rdfm_artifact_gui_script
    create_rdfm_artifact_cli_script
    add_to_path

    echo ""
    echo "======================================"
    echo "  Installation Complete!"
    echo "======================================"
    echo ""


    # Detect shell for instructions
    CURRENT_SHELL=$(basename "$SHELL")
    case "$CURRENT_SHELL" in
        zsh)
            SHELL_RC="~/.zshrc"
            ;;
        fish)
            SHELL_RC="~/.config/fish/config.fish"
            ;;
        *)
            SHELL_RC="~/.bashrc"
            ;;
    esac

    log_info "To use the installed commands, either:"
    echo ""
    log_info "  1. Restart your terminal, or"
    log_info "  2. Run: source $SHELL_RC"
    echo ""
    log_info "Available commands:"
    log_success "  rdfm-artifact-gui  - Standalone Artifact Tool"
    log_success "  rdfm-artifact  - RDFM Artifact CLI"

    echo ""
}

# Native installation
install_native() {
    # Pass all remaining arguments to install-native.sh
    exec "$SCRIPT_DIR/native-install.sh" "$@"
}

# Parse Docker-specific arguments
parse_docker_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --no-cache)
                NO_CACHE=1
                shift
                ;;
            --help|-h)
                show_usage
                ;;
            *)
                log_error "Unknown Docker option: $1"
                show_usage
                ;;
        esac
    done
}

# Main
main() {
    if [[ $# -lt 1 ]]; then
        show_usage
    fi

    local install_method="$1"
    shift

    case "$install_method" in
        docker)
            # Parse Docker-specific arguments
            parse_docker_args "$@"
            install_docker
            ;;
        native)
            install_native "$@"
            ;;
        --help|-h)
            show_usage
            ;;
        *)
            log_error "Unknown installation method: $install_method"
            show_usage
            ;;
    esac
}

main "$@"
