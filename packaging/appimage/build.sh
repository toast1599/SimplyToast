#!/usr/bin/env bash
set -euo pipefail

VERSION="$1"

export ARCH=x86_64
export APPIMAGE_ARCH=x86_64

ROOT=/build
OUT=/out
APPDIR=/tmp/AppDir

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/512x512/apps"

# Extract artifact
tar -xzf "$ROOT/artifact.tar.gz" -C "$APPDIR/usr"

# Metadata
install -Dm755 "$ROOT/AppRun" "$APPDIR/AppRun"
install -Dm644 "$ROOT/simplytoast.desktop" \
  "$APPDIR/usr/share/applications/simplytoast.desktop"

install -Dm644 "$APPDIR/usr/data/icons/com.toast1599.SimplyToast-512.png" \
  "$APPDIR/usr/share/icons/hicolor/512x512/apps/com.toast1599.SimplyToast.png"

chmod +x "$APPDIR/AppRun"

# ✅ CORRECT linuxdeploy INVOCATION
env ARCH=x86_64 linuxdeploy \
  --appdir "$APPDIR" \
  --desktop-file "$APPDIR/usr/share/applications/simplytoast.desktop" \
  --icon-file "$APPDIR/usr/share/icons/hicolor/512x512/apps/com.toast1599.SimplyToast.png" \
  --output appimage

# Move result
mv *.AppImage "$OUT/SimplyToast-${VERSION}-x86_64.AppImage"
