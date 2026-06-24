#!/bin/bash
#
# Build a self-contained AppImage for the RDFM Artifact GUI.
#
# Produces a single executable that bundles its own Python + Tcl/Tk, the
# application and its Python deps, and the compiled rdfm-artifact Go binary with
# the shared libraries it needs. Runs on any glibc Linux with AppImage support;
# no host Python, Tk, Go, or Docker required at runtime (host Docker is used
# only for docker-type artifacts, if present).
#
# Requirements on the BUILD machine:
#   - docker            (to compile rdfm-artifact via the project Dockerfile)
#   - curl              (to download the relocatable Python)
#   - appimagetool      (on PATH, or set APPIMAGETOOL=/path/to/appimagetool)
#
# Usage:
#   ./scripts/build-appimg.sh
#
# Environment overrides:
#   APPIMAGETOOL   Path to appimagetool (default: first on PATH)
#   PYTHON_VERSION python-build-standalone version tag (see PY_* below)
#   OUTPUT         Output AppImage path (default: build/RDFM-Artifact-GUI-x86_64.AppImage)

set -euo pipefail

# --- Paths -------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
APPDIR="$BUILD_DIR/AppDir"
OUTPUT="${OUTPUT:-$BUILD_DIR/RDFM-Artifact-GUI-x86_64.AppImage}"
# Checked-in AppImage root files (AppRun, .desktop) copied into the AppDir.
TEMPLATE_DIR="$SCRIPT_DIR/appimage"

# --- Pinned dependencies -----------------------------------------------------
# Relocatable CPython that bundles Tcl/Tk (the distribution uv/rye use). The
# install_only x86_64-gnu build runs from any directory, which is what makes a
# portable Tkinter AppImage possible.
PY_RELEASE="20260610"
PY_VERSION="${PYTHON_VERSION:-3.12.13}"
PY_TARBALL="cpython-${PY_VERSION}+${PY_RELEASE}-x86_64-unknown-linux-gnu-install_only.tar.gz"
PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PY_RELEASE}/${PY_TARBALL}"

# Docker image / paths for the rdfm-artifact builder stage (see Dockerfile).
BUILDER_IMAGE="rdfm-artifact-builder"
BINARY_IN_IMAGE="/build/rdfm/tools/rdfm-artifact/rdfm-artifact"

# --- Logging -----------------------------------------------------------------
log()  { echo -e "\033[0;34m[INFO]\033[0m $*"; }
ok()   { echo -e "\033[0;32m[ OK ]\033[0m $*"; }
die()  { echo -e "\033[0;31m[FAIL]\033[0m $*" >&2; exit 1; }

# --- Preflight ---------------------------------------------------------------
command -v docker >/dev/null || die "docker not found on PATH"
command -v curl   >/dev/null || die "curl not found on PATH"

APPIMAGETOOL="${APPIMAGETOOL:-$(command -v appimagetool || true)}"
[ -n "$APPIMAGETOOL" ] && [ -x "$APPIMAGETOOL" ] || die \
  "appimagetool not found. Put it on PATH or set APPIMAGETOOL=/path/to/appimagetool"

# =============================================================================
# Step 1: AppDir skeleton (clean each run so builds are reproducible)
# =============================================================================
log "Preparing AppDir at $APPDIR"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib" "$APPDIR/usr/python"

# =============================================================================
# Step 2: Bundle a relocatable Python (with Tcl/Tk)
# =============================================================================
PY_CACHE="$BUILD_DIR/$PY_TARBALL"
if [ ! -f "$PY_CACHE" ]; then
    log "Downloading python-build-standalone $PY_VERSION ($PY_RELEASE)"
    curl -fL -o "$PY_CACHE" "$PY_URL"
else
    log "Using cached Python tarball: $PY_CACHE"
fi
log "Extracting Python into AppDir"
tar -xzf "$PY_CACHE" -C "$APPDIR/usr/python" --strip-components=1
PYBIN="$APPDIR/usr/python/bin/python3"

# Sanity: the whole point is a working bundled Tkinter.
"$PYBIN" -c "import tkinter" \
    || die "bundled Python cannot import tkinter — Tk bundling failed"
ok "Bundled Python: $("$PYBIN" --version)"

# =============================================================================
# Step 3: Install the application (+ Pillow, PyYAML, assets) into the bundle
# =============================================================================
log "Installing artifact_gui into the bundled Python"
"$PYBIN" -m pip install --no-cache-dir "$PROJECT_DIR" >/dev/null
ok "Application installed into bundle"

# =============================================================================
# Step 4: Build rdfm-artifact in Docker and extract it + its shared libs
# =============================================================================
log "Building rdfm-artifact (Docker builder stage)"
docker build --target builder -t "$BUILDER_IMAGE" "$PROJECT_DIR" >/dev/null \
    || die "docker build failed"

log "Creating extraction container"
cid="$(docker create "$BUILDER_IMAGE")"
# Always remove the container, even if a later step fails.
trap 'docker rm -f "$cid" >/dev/null 2>&1 || true' EXIT

log "Copying rdfm-artifact binary"
docker cp "$cid:$BINARY_IN_IMAGE" "$APPDIR/usr/bin/rdfm-artifact"

log "Copying the binary's shared-library closure"
# Resolve the dependency closure inside the image in ONE invocation. ldd gives
# the SONAME path (e.g. liblzma.so.5), which is often a symlink to a versioned
# real file; readlink -f *inside the container* yields the real file so we copy
# real content out under the SONAME the loader searches for. glibc core and the
# loader are excluded on purpose since bundling those breaks portability.
libs="$(docker run --rm "$BUILDER_IMAGE" sh -c "
  ldd '$BINARY_IN_IMAGE' \
    | grep '=>' \
    | grep -oE '/[^ ]+' \
    | grep -vE 'ld-linux|libc\.so|libm\.so|libpthread|libdl\.so|librt\.so' \
    | while read -r p; do printf '%s\t%s\n' \"\$(basename \"\$p\")\" \"\$(readlink -f \"\$p\")\"; done
")"
echo "$libs" | while IFS=$'\t' read -r soname real; do
    [ -z "$soname" ] && continue
    docker cp "$cid:$real" "$APPDIR/usr/lib/$soname"
done

docker rm -f "$cid" >/dev/null
trap - EXIT
ok "Extracted rdfm-artifact and $(ls "$APPDIR/usr/lib" | wc -l) shared lib(s)"

# =============================================================================
# Step 5: AppDir root files: AppRun, .desktop, icon
# =============================================================================
log "Copying AppRun, .desktop, and icon into AppDir"
cp "$TEMPLATE_DIR/AppRun" "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"
cp "$TEMPLATE_DIR/rdfm-artifact-gui.desktop" "$APPDIR/rdfm-artifact-gui.desktop"
cp "$PROJECT_DIR/artifact_gui/assets/app_icon.png" "$APPDIR/rdfm-artifact-gui.png"

# =============================================================================
# Step 6: Package the AppDir into the final AppImage
# =============================================================================
log "Packaging AppImage with appimagetool"
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$OUTPUT" >/dev/null \
    || die "appimagetool failed"

ok "Built $OUTPUT ($(du -h "$OUTPUT" | cut -f1))"
