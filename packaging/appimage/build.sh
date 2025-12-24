#!/usr/bin/env bash
set -euo pipefail

VERSION="$1"

# 1. Force ARCH for the shell and all child processes
export ARCH=x86_64
export APPIMAGE_ARCH=x86_64

ROOT=/build
OUT=/out
APPDIR=/tmp/AppDir

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/512x512/apps"

# 2. Extract artifact
tar -xzf "$ROOT/artifact.tar.gz" -C "$APPDIR/usr"

# 3. Setup Metadata
install -Dm755 "$ROOT/AppRun" "$APPDIR/AppRun"
install -Dm644 "$ROOT/simplytoast.desktop" "$APPDIR/usr/share/applications/"
install -Dm644 "$APPDIR/usr/data/icons/com.toast1599.SimplyToast-512.png" \
  "$APPDIR/usr/share/icons/hicolor/512x512/apps/com.toast1599.SimplyToast.png" || true

# 4. Permissions (Essential even for Python)
chmod +x "$APPDIR/AppRun"

# 5. THE FIX: Pass ARCH directly into the environment of the command execution
# We use 'env' to ensure the plugin sees the variable inside the container.
env ARCH=x86_64 linuxdeploy --appimage-extract-and-run \
  --appdir "$APPDIR" \
  --plugin appimage \
  --output appimage

# 6. Cleanup/Move
mv SimplyToast-*.AppImage "$OUT/SimplyToast-${VERSION}-x86_64.AppImage"