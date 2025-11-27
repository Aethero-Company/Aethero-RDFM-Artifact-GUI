# Aethero RDFM GUI

A Python/Tkinter desktop application that provides a graphical interface for RDFM Artifact CLI.

## Docker Installation (Recommended)

The recommended way to run RDFM Artifact GUI is using Docker, which bundles all dependencies and works on any OS. This method may also drastically reduce the storage space needed for installation depending on which dependencies your system already has.

The launch scripts for the docker container (`rdfm-artifact` and `rdfm-artifact-gui`) map the host user home directory into the home directory of the container user so that file access in the container is 1:1 with the host.

### Prerequisites

- Docker Engine 20.10+ or Docker Desktop
- For GUI mode: X11 display server (Linux) or XQuartz (macOS)

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Aethero-Company/Aethero-RDFM-Artifact-GUI
   cd Aethero-RDFM-Artifact-GUI
   ```

2. **Installation**
   ```bash
   ./scripts/install.sh docker
   ```
   Note that you may need to restart your shell for the application to be on your PATH.

3. **Run the application**
   ```bash
   rdfm-artifact-gui
   ```

4. **Use the CLI**

   If access to the rdfm-artifact CLI is needed, it can be accessed with 
   ```bash
   rdfm-artifact
   ```
   which exposes the CLI through the docker container.

**Note for X11 forwarding:**
- **Linux**: Should work out of the box
- **Windows**: Run through WSL on a distro that supports WSL GUI applications (e.g. Ubuntu)

### File Permissions

The Docker image is built with your user's UID/GID to ensure files created by `rdfm-artifact` are owned by your host user, not root.

## Native Installation

If you prefer to run without Docker, the application can also be installed natively. This method also installs rdfm-artifact directly onto the system. 

This method has the following dependencies:

1. CMake >= 3.25.1
2. Go >= 1.20

### Automated installer

The automated installation script handles all dependencies for common Linux distributions:

```bash
git clone https://github.com/Aethero-Company/Aethero-RDFM-Artifact-GUI
cd Aethero-RDFM-Artifact-GUI
./scripts/install.sh native
```

**Options**:
```bash
# Skip system dependencies (if already installed)
./scripts/install.sh native --skip-deps

# Skip installing GUI (if only rdfm-artifact CLI is desired)
./scripts/install.sh native --skip-gui
```

After installation, start the application:
```bash
# Artifact GUI
rdfm-artifact-gui
```
Note that you may need to restart your shell for the application to be on your PATH.

## Uninstalling

### Uninstalling Docker Verison

**Remove the run scripts**
```bash
rm ~/.local/bin/rdfm-artifact-gui
rm ~/.local/bin/rdfm-artifact
```
**Remove the docker image**
```bash
docker image rm aethero/rdfm-artifact-gui
```

### Uninstalling Native Version

**rdfm-artifact**:
```bash
rm ~/.local/bin/rdfm-artifact
```
**GUI**:
```bash
pipx uninstall rdfm-artifact-gui
```

## Development

For development, install with dev dependencies:

```bash
pip install -e '.[dev]'
```

This project uses [ruff](https://github.com/astral-sh/ruff) for code formatting and linting