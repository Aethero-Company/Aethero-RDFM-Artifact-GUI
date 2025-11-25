# Multi-stage Dockerfile for RDFM GUI with rdfm-artifact and rdfm-mgmt
# Based on Ubuntu 24.04 for Python 3.12+ support

# =============================================================================
# Stage 1: Build rdfm-artifact from source
# =============================================================================
FROM ubuntu:24.04 AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    cmake \
    liblzma-dev \
    libglib2.0-dev \
    libssl-dev \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Go
ARG GO_VERSION=1.21.6
RUN wget -q https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz \
    && rm go${GO_VERSION}.linux-amd64.tar.gz
ENV PATH="$PATH:/usr/local/go/bin"

# Build go-xdelta
RUN git clone --depth 1 https://github.com/antmicro/go-xdelta.git \
    && mkdir go-xdelta/build \
    && cd go-xdelta/build \
    && cmake -DCGO_INTEGRATION=ON -DENCODER=ON .. \
    && make -j$(nproc) \
    && make install

# Clone RDFM repository and build rdfm-artifact
RUN git clone --depth 1 https://github.com/antmicro/rdfm.git \
    && cd rdfm/tools/rdfm-artifact \
    && make

# =============================================================================
# Stage 2: Runtime image with rdfm-mgmt and GUI
# =============================================================================
FROM ubuntu:24.04 AS runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python and Tkinter for GUI
    python3 \
    python3-tk \
    python3-pil \
    python3-pil.imagetk \
    python3-pip \
    python3-venv \
    pipx \
    # Runtime libraries for rdfm-artifact
    liblzma5 \
    libglib2.0-0 \
    libssl3 \
    # Git for pipx install from repo
    git \
    ca-certificates \
    # X11 libraries for GUI forwarding
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxft2 \
    libfontconfig1 \
    # Fonts for better GUI rendering
    fonts-dejavu-core \
    # Docker CLI for docker save functionality
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy rdfm-artifact binary from builder
COPY --from=builder /build/rdfm/tools/rdfm-artifact/rdfm-artifact /usr/local/bin/

# Copy go-xdelta shared libraries
COPY --from=builder /usr/local/lib/libxdelta3* /usr/local/lib/
RUN ldconfig

# Set up pipx to install to system-wide location
ENV PIPX_HOME=/opt/pipx
ENV PIPX_BIN_DIR=/usr/local/bin

# Create user with matching host UID/GID
ARG UNAME=rdfm-user
ARG UID=1000
ARG GID=1000

# Remove any existing user/group with conflicting UID/GID, then create new ones
# Also add user to docker group for socket access
RUN if getent passwd $UID > /dev/null 2>&1; then userdel -f $(getent passwd $UID | cut -d: -f1); fi \
    && if getent group $GID > /dev/null 2>&1; then groupdel $(getent group $GID | cut -d: -f1) 2>/dev/null || true; fi \
    && groupadd -g $GID $UNAME \
    && useradd -m -u $UID -g $GID -s /bin/bash $UNAME \
    && usermod -aG docker $UNAME

# Create config directory for rdfm-mgmt
RUN chown -R $UID:$GID /home/$UNAME

# Copy application files
COPY --chown=$UID:$GID ./app /app/app/
COPY ./pyproject.toml /app/pyproject.toml

RUN pipx install /app

# Set up environment for the user
USER $UNAME
ENV HOME=/home/$UNAME
ENV PATH="/usr/local/bin:$PATH"

# Default command - can be overridden
CMD ["rdfm-artifact-gui"]
