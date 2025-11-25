#!/bin/bash
#
# RDFM GUI Native Installation Script
#
# This script installs rdfm-artifact and the artifact GUI by default.
# Use --full to also install rdfm-mgmt for complete device management.
#
# Usage:
#   ./scripts/install-native.sh [OPTIONS]
#
# Options:
#   --skip-gui         Skip installing rdfm-gui
#   --skip-deps        Skip installing system dependencies
#   --help             Show this help message
#

set -e

print_help() {
    echo "RDFM GUI Native Installation Script"
    echo ""
    echo "This script installs both rdfm-artifact and the artifact GUI by default."
    echo ""
    echo "Usage:"
    echo "./scripts/install-native.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "--skip-gui         Skip installing rdfm-gui"
    echo "--skip-deps        Skip installing system dependencies"
    echo "-h|--help             Show this help message"
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
SKIP_GUI=false
SKIP_DEPS=false
INSTALL_DIR="$HOME/.local/bin"

# Determine project directory at script start (before any cd commands)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-gui)
            SKIP_GUI=true
            shift
            ;;
        --skip-deps)
            SKIP_DEPS=true
            shift
            ;;
        -h|--help)
            print_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            print_help
            exit 1
            ;;
    esac
done

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

# Version comparison function
# Returns 0 if version1 >= version2, 1 otherwise
version_ge() {
    local version1="$1"
    local version2="$2"

    # Use sort -V to compare versions
    if [[ "$(printf '%s\n' "$version2" "$version1" | sort -V | head -n1)" == "$version2" ]]; then
        return 0
    else
        return 1
    fi
}

# Get available package version from apt
get_apt_version() {
    local package="$1"
    apt-cache policy "$package" 2>/dev/null | grep -oP 'Candidate: \K[\d.]+' | head -1
}

# Get available package version from dnf
get_dnf_version() {
    local package="$1"
    dnf info "$package" 2>/dev/null | grep -oP '^Version\s*:\s*\K[\d.]+' | head -1
}

# Get available package version from pacman
get_pacman_version() {
    local package="$1"
    pacman -Si "$package" 2>/dev/null | grep -oP '^Version\s*:\s*\K[\d.]+' | head -1
}

# Get available package version from zypper
get_zypper_version() {
    local package="$1"
    zypper info "$package" 2>/dev/null | grep -oP '^Version\s*:\s*\K[\d.]+' | head -1
}

# Check if a requirement is met or can be installed
# Returns: 0 = already installed, 1 = needs install, 2 = error (unavailable)
# Sets NEED_INSTALL_<tool> variable
check_requirement() {
    local tool_name="$1"
    local tool_cmd="$2"
    local required_version="$3"
    local pkg_name="$4"
    local available_version="$5"

    # Check if already installed with correct version
    if command -v "$tool_cmd" &> /dev/null; then
        local installed_version
        case "$tool_cmd" in
            python3)
                installed_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+(\.\d+)?' | head -1)
                ;;
            cmake)
                installed_version=$(cmake --version 2>&1 | head -1 | grep -oP '\d+\.\d+(\.\d+)?' | head -1)
                ;;
            go)
                installed_version=$(go version 2>&1 | grep -oP '\d+\.\d+(\.\d+)?' | head -1)
                ;;
        esac

        if version_ge "$installed_version" "$required_version"; then
            log_success "$tool_name $installed_version >= $required_version (already installed)"
            return 0
        else
            log_warn "$tool_name $installed_version is too old (need >= $required_version)"
        fi
    fi

    # Check if package manager has a suitable version
    if [ -z "$available_version" ]; then
        log_error "$tool_name is not available in package manager"
        return 2
    fi

    if version_ge "$available_version" "$required_version"; then
        log_info "$tool_name $available_version >= $required_version available, will install"
        return 1
    else
        log_error "$tool_name $available_version < $required_version (required)"
        log_info "  Your package manager does not have a recent enough version."
        log_info "  Please install $tool_name >= $required_version manually or use a newer distribution."
        return 2
    fi
}

# Run pipx install with retry logic
run_pipx_install() {
    local package="$1"
    local max_retries=3
    local retry_count=0

    while [ $retry_count -lt $max_retries ]; do
        if [ $retry_count -gt 0 ]; then
            log_info "Retrying pipx install (attempt $((retry_count + 1))/$max_retries)..."
            sleep 2
        fi

        if pipx install "$package"; then
            return 0
        else
            retry_count=$((retry_count + 1))
            if [ $retry_count -lt $max_retries ]; then
                log_warn "pipx install failed, will retry..."
            fi
        fi
    done

    log_error "pipx install failed after $max_retries attempts"
    return 1
}

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    log_error "This script is designed for Linux systems only."
    log_info "For macOS, see the README for manual installation instructions."
    exit 1
fi

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        DISTRO_LIKE=$ID_LIKE
        VERSION=$VERSION_ID
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        DISTRO=$DISTRIB_ID
        VERSION=$DISTRIB_RELEASE
    else
        DISTRO="unknown"
    fi
}

detect_distro
log_info "Detected distribution: $DISTRO (version: ${VERSION:-unknown})"

# Install system dependencies based on distribution
install_system_deps() {
    log_info "Installing system dependencies..."

    case $DISTRO in
        ubuntu|debian|linuxmint|pop)
            sudo apt-get update

            # Check requirements and determine what needs to be installed
            local version_errors=0
            local install_cmake=false
            local install_go=false

            log_info "Checking requirements..."

            # Check build tool versions if rdfm-artifact is being built
            CMAKE_AVAIL=$(get_apt_version "cmake")
            local result=0
            check_requirement "CMake" "cmake" "3.25.1" "cmake" "$CMAKE_AVAIL" || result=$?
            case $result in
                1) install_cmake=true ;;
                2) version_errors=$((version_errors + 1)) ;;
            esac

            GO_AVAIL=$(get_apt_version "golang-go")
            result=0
            check_requirement "Go" "go" "1.20" "golang-go" "$GO_AVAIL" || result=$?
            case $result in
                1) install_go=true ;;
                2) version_errors=$((version_errors + 1)) ;;
            esac

            if [ $version_errors -gt 0 ]; then
                log_error "Required package versions not available in apt repositories."
                log_info "Consider upgrading to a newer distribution version."
                exit 1
            fi

            # Core dependencies including pipx
            sudo apt-get install -y \
                python3 \
                python3-tk \
                python3-pip \
                python3-venv \
                pipx \
                git \
                curl

            # Ensure pipx is properly initialized
            pipx ensurepath &>/dev/null || true

            # Build dependencies for rdfm-artifact
            log_info "Installing build dependencies for rdfm-artifact..."
            sudo apt-get install -y \
                golang-go \
                cmake \
                build-essential \
                liblzma-dev \
                libglib2.0-dev \
                libssl-dev
            ;;

        fedora|rhel|centos|rocky|alma)
            sudo dnf update -y

            # Check requirements and determine what needs to be installed
            local version_errors=0
            local install_cmake=false
            local install_go=false

            log_info "Checking requirements..."

            # Check build tool versions if rdfm-artifact is being built
            CMAKE_AVAIL=$(get_dnf_version "cmake")
            local result=0
            check_requirement "CMake" "cmake" "3.25.1" "cmake" "$CMAKE_AVAIL" || result=$?
            case $result in
                1) install_cmake=true ;;
                2) version_errors=$((version_errors + 1)) ;;
            esac

            GO_AVAIL=$(get_dnf_version "golang")
            result=0
            check_requirement "Go" "go" "1.20" "golang" "$GO_AVAIL" || result=$?
            case $result in
                1) install_go=true ;;
                2) version_errors=$((version_errors + 1)) ;;
            esac

            if [ $version_errors -gt 0 ]; then
                log_error "Required package versions not available in dnf repositories."
                log_info "Consider upgrading to a newer distribution version."
                exit 1
            fi

            # Core dependencies
            sudo dnf install -y \
                python3 \
                python3-tkinter \
                python3-pip \
                git \
                curl

            # Install pipx
            if ! command -v pipx &> /dev/null; then
                sudo dnf install -y pipx || python3 -m pip install --user pipx
            fi
            # Ensure pipx is properly initialized
            pipx ensurepath &>/dev/null || true

            # Build dependencies for rdfm-artifact
            log_info "Installing build dependencies for rdfm-artifact..."
            sudo dnf install -y \
                golang \
                cmake \
                gcc \
                gcc-c++ \
                make \
                xz-devel \
                glib2-devel \
                openssl-devel
            ;;

        arch|manjaro|endeavouros)
            sudo pacman -Syu --noconfirm

            # Check requirements and determine what needs to be installed
            local version_errors=0
            local install_cmake=false
            local install_go=false

            log_info "Checking requirements..."

            # Check build tool versions if rdfm-artifact is being built
            CMAKE_AVAIL=$(get_pacman_version "cmake")
            local result=0
            check_requirement "CMake" "cmake" "3.25.1" "cmake" "$CMAKE_AVAIL" || result=$?
            case $result in
                1) install_cmake=true ;;
                2) version_errors=$((version_errors + 1)) ;;
            esac

            GO_AVAIL=$(get_pacman_version "go")
            result=0
            check_requirement "Go" "go" "1.20" "go" "$GO_AVAIL" || result=$?
            case $result in
                1) install_go=true ;;
                2) version_errors=$((version_errors + 1)) ;;
            esac

            if [ $version_errors -gt 0 ]; then
                log_error "Required package versions not available in pacman repositories."
                log_info "Consider updating your system or using AUR packages."
                exit 1
            fi

            # Core dependencies
            sudo pacman -S --noconfirm \
                python \
                tk \
                python-pip \
                python-pipx \
                git \
                curl

            # Ensure pipx is properly initialized
            pipx ensurepath &>/dev/null || true

            # Build dependencies for rdfm-artifact
            log_info "Installing build dependencies for rdfm-artifact..."
            sudo pacman -S --noconfirm \
                go \
                cmake \
                base-devel \
                xz \
                glib2 \
                openssl
            ;;

        opensuse*|suse)
            sudo zypper refresh

            # Check requirements and determine what needs to be installed
            local version_errors=0
            local install_cmake=false
            local install_go=false

            log_info "Checking requirements..."

            # Check build tool versions if rdfm-artifact is being built
            CMAKE_AVAIL=$(get_zypper_version "cmake")
            local result=0
            check_requirement "CMake" "cmake" "3.25.1" "cmake" "$CMAKE_AVAIL" || result=$?
            case $result in
                1) install_cmake=true ;;
                2) version_errors=$((version_errors + 1)) ;;
            esac

            GO_AVAIL=$(get_zypper_version "go")
            result=0
            check_requirement "Go" "go" "1.20" "go" "$GO_AVAIL" || result=$?
            case $result in
                1) install_go=true ;;
                2) version_errors=$((version_errors + 1)) ;;
            esac

            if [ $version_errors -gt 0 ]; then
                log_error "Required package versions not available in zypper repositories."
                log_info "Consider upgrading to a newer distribution version."
                exit 1
            fi

            # Core dependencies
            sudo zypper install -y \
                python3 \
                python3-tk \
                python3-pip \
                git \
                curl

            # Install pipx
            if ! command -v pipx &> /dev/null; then
                python3 -m pip install --user pipx
            fi
            # Ensure pipx is properly initialized
            pipx ensurepath &>/dev/null || true

            # Build dependencies for rdfm-artifact
            log_info "Installing build dependencies for rdfm-artifact..."
            sudo zypper install -y \
                go \
                cmake \
                gcc \
                gcc-c++ \
                make \
                xz-devel \
                glib2-devel \
                libopenssl-devel
            ;;

        *)
            log_error "Unsupported distribution: $DISTRO"
            log_info "Please install dependencies manually:"
            log_info "  - Python 3.11+"
            log_info "  - Tkinter (python3-tk)"
            log_info "  - pipx"
            log_info "  - git"
            log_info "For rdfm-artifact:"
            log_info "  - Go 1.20+"
            log_info "  - CMake"
            log_info "  - Build tools (gcc, make)"
            log_info "  - liblzma, libglib2.0, libssl"
            exit 1
            ;;
    esac

    log_success "System dependencies installed"
}

# Build and install rdfm-artifact
install_rdfm_artifact() {
    log_info "Building rdfm-artifact (this may take a few minutes)..."

    # Save current directory to return to after build
    local ORIGINAL_DIR="$(pwd)"

    # Create install directory if it doesn't exist
    mkdir -p "$INSTALL_DIR"

    # Clone rdfm repository
    TEMP_DIR=$(mktemp -d)
    git clone --depth 1 https://github.com/antmicro/rdfm.git "$TEMP_DIR/rdfm"

    # Build go-xdelta first
    log_info "Building go-xdelta library..."
    git clone --depth 1 https://github.com/antmicro/go-xdelta.git "$TEMP_DIR/go-xdelta"
    cd "$TEMP_DIR/go-xdelta"
    mkdir -p build && cd build
    cmake -DCGO_INTEGRATION=ON -DENCODER=ON ..
    make -j$(nproc)
    sudo make install
    sudo ldconfig

    # Build rdfm-artifact
    log_info "Building rdfm-artifact..."
    cd "$TEMP_DIR/rdfm/tools/rdfm-artifact"
    make

    # Install binary
    cp rdfm-artifact "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/rdfm-artifact"

    # Return to original directory before cleanup
    cd "$ORIGINAL_DIR"

    # Cleanup
    rm -rf "$TEMP_DIR"

    log_success "rdfm-artifact installed to $INSTALL_DIR/rdfm-artifact"
    log_info "Verify with: rdfm-artifact --help"

    # Check if install directory is in PATH
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        log_warn "$INSTALL_DIR is not in your PATH"
        log_info "Add it to your shell profile:"
        log_info "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
    fi
}

# Install rdfm-gui
install_rdfm_gui() {
    log_info "Installing rdfm-gui..."

    # Install rdfm-gui using pipx with retry logic (PROJECT_DIR set at script start)
    if ! run_pipx_install "$PROJECT_DIR"; then
        exit 1
    fi

    log_success "rdfm-artifact-gui installed successfully"
    log_info "Run with: rdfm-artifact-gui"
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

# Main installation flow
main() {
    echo ""
    echo "======================================"
    echo "  RDFM Artifact Tool Installation"
    echo "======================================"
    echo ""

    # Set PATH once for all operations (pipx installs to ~/.local/bin)
    export PATH="$HOME/.local/bin:$PATH"

    # Install system dependencies
    if [ "$SKIP_DEPS" = false ]; then
        install_system_deps
    else
        log_info "Skipping system dependencies installation"
    fi

    # Build and install rdfm-artifact
    install_rdfm_artifact

    # Install rdfm-gui
    if [ "$SKIP_GUI" = false ]; then
        install_rdfm_gui
    else
        log_info "Skipping rdfm-gui installation"
    fi

    add_to_path

    echo ""
    echo "======================================"
    echo "  Installation Complete!"
    echo "======================================"
    echo ""

    # Detect user's shell and provide appropriate instructions
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
    log_info "Or run immediately with full path:"
    log_info "  $HOME/.local/bin/rdfm-artifact-gui"
    echo ""

    # Verify installations
    log_info "Verifying installations..."

    if command -v rdfm-artifact &> /dev/null; then
        log_success "rdfm-artifact: $(which rdfm-artifact)"
    elif [ -f "$INSTALL_DIR/rdfm-artifact" ]; then
        log_success "rdfm-artifact: $INSTALL_DIR/rdfm-artifact"
    else
        log_warn "rdfm-artifact not found"
    fi

    # Check for rdfm-artifact-gui (always installed)
    if command -v rdfm-artifact-gui &> /dev/null; then
        log_success "rdfm-artifact-gui: $(which rdfm-artifact-gui)"
    elif [ -f "$HOME/.local/bin/rdfm-artifact-gui" ]; then
        log_success "rdfm-artifact-gui: $HOME/.local/bin/rdfm-artifact-gui"
    else
        log_warn "rdfm-artifact-gui not found"
    fi
}

main "$@"
