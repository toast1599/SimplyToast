#!/bin/bash
set -e

VERSION="$1"

if [ -z "$VERSION" ]; then
    echo "Usage: ./build_all.sh <version>"
    exit 1
fi

echo "== Building SimplyToast v$VERSION =="

rm -rf dist
mkdir dist

# -------------------------
# Build .deb package
# -------------------------
echo "[1/2] Building DEB..."
rm -rf deb_build
mkdir -p deb_build/usr/bin
mkdir -p deb_build/usr/share/simplytoast
mkdir -p deb_build/usr/share/applications
mkdir -p deb_build/usr/share/icons/hicolor/512x512/apps
mkdir -p deb_build/DEBIAN

install -Dm755 src/main.py deb_build/usr/bin/simplytoast
cp -r assets data deb_build/usr/share/simplytoast/
cp data/com.toast1599.SimplyToast.desktop deb_build/usr/share/applications/
cp data/com.toast1599.SimplyToast.png deb_build/usr/share/icons/hicolor/512x512/apps/
# AppStream metadata
mkdir -p deb_build/usr/share/metainfo
cp data/com.toast1599.SimplyToast.appdata.xml deb_build/usr/share/metainfo/
cat > deb_build/DEBIAN/control <<EOF
Package: simplytoast
Version: $VERSION
Architecture: all
Maintainer: toast1599
Description: Startup application manager
EOF

dpkg-deb --build deb_build dist/simplytoast_${VERSION}.deb

# -------------------------
# Build AppImage
# -------------------------
echo "[2/2] Building AppImage..."

rm -rf AppDir
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/simplytoast
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/512x512/apps
mkdir -p AppDir/usr/share/metainfo

# Copy app code
install -Dm755 src/main.py AppDir/usr/bin/simplytoast

# Copy data + assets
cp -r assets data AppDir/usr/share/simplytoast/

# Copy desktop + icon
cp data/com.toast1599.SimplyToast.desktop AppDir/usr/share/applications/
cp data/com.toast1599.SimplyToast.png AppDir/usr/share/icons/hicolor/512x512/apps/

# Copy AppStream metadata
cp data/com.toast1599.SimplyToast.appdata.xml AppDir/usr/share/metainfo/

# Build AppImage
ARCH=x86_64 ./linuxdeploy-x86_64.AppImage --appdir AppDir --output appimage

# Rename output file
APPIMAGE_FILE=$(ls SimplyToast-*.AppImage | head -n 1)
mv "$APPIMAGE_FILE" "dist/SimplyToast-$VERSION.AppImage"

echo "== DONE =="
ls -lh dist
