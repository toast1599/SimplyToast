#!/bin/bash
set -e

VERSION="$1"

if [ -z "$VERSION" ]; then
    echo "Usage: ./build_all.sh <version>"
    exit 1
fi

# Verify clean git tree
if [ -n "$(git status --porcelain)" ]; then
    echo "[ERR] Git working tree is dirty. Commit or stash changes before running this script."
    git status --short
    exit 1
fi

echo "[*] Starting build pipeline for SimplyToast v$VERSION"

rm -rf dist
mkdir dist

# -------------------------
# Build .deb package
# -------------------------
echo "[1/3] Building DEB..."
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
echo "[2/3] Building AppImage..."

rm -rf AppDir
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/simplytoast
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/512x512/apps
mkdir -p AppDir/usr/share/metainfo

install -Dm755 src/main.py AppDir/usr/bin/simplytoast
cp -r assets data AppDir/usr/share/simplytoast/
cp data/com.toast1599.SimplyToast.desktop AppDir/usr/share/applications/
cp data/com.toast1599.SimplyToast.png AppDir/usr/share/icons/hicolor/512x512/apps/
cp data/com.toast1599.SimplyToast.appdata.xml AppDir/usr/share/metainfo/

ARCH=x86_64 ./linuxdeploy-x86_64.AppImage --appdir AppDir --output appimage

APPIMAGE_FILE=$(ls SimplyToast-*.AppImage | head -n 1)
mv "$APPIMAGE_FILE" "dist/SimplyToast-$VERSION.AppImage"

# -------------------------
# Build SNAP
# -------------------------
echo "[3/3] Building SNAP..."

rm -rf prime parts stage snap/.snapcraft

sed -i "s/^version:.*/version: '$VERSION'/" snap/snapcraft.yaml

if snap list lxd >/dev/null 2>&1; then
    snapcraft --use-lxd
else
    snapcraft --destructive-mode
fi

SNAP_FILE=$(ls *.snap | grep simplytoast | head -n 1)
mv "$SNAP_FILE" "dist/simplytoast_${VERSION}_amd64.snap"

echo "[SNAP] Done."

# -------------------------
# Upload Snap to Snap Store
# -------------------------
echo "[SNAPSTORE] Uploading to Snap Store (edge channel)..."

if snapcraft upload "dist/simplytoast_${VERSION}_amd64.snap" --release=edge; then
    echo "[SNAPSTORE] Snap uploaded to 'edge'."
else
    echo "[SNAPSTORE] Upload failed."
    exit 1
fi

# -------------------------
# GitHub Release Automation
# -------------------------
echo "[UPLOAD] Creating GitHub release..."

if gh release view "v$VERSION" >/dev/null 2>&1; then
    gh release delete "v$VERSION" --yes || true
    git tag -d "v$VERSION" || true
fi

git tag "v$VERSION"
git push origin "v$VERSION"

gh release create "v$VERSION" dist/* \
    --title "SimplyToast v$VERSION" \
    --notes "Automated release for version $VERSION."

echo "[UPLOAD] GitHub release ready."

# -------------------------
# Update APT Repository
# -------------------------
APT_REPO="/home/toast1599/simplytoast-apt"
echo "[APT] Updating APT repo at $APT_REPO"

cp "dist/simplytoast_${VERSION}.deb" "$APT_REPO/pool/main/s/"

cd "$APT_REPO"
dpkg-scanpackages pool /dev/null > Packages
gzip -9c Packages > Packages.gz

cp Packages dists/stable/
cp Packages.gz dists/stable/

apt-ftparchive release dists/stable > dists/stable/Release

gpg --default-key "toast1599" --clearsign -o dists/stable/InRelease dists/stable/Release
gpg --default-key "toast1599" -abs -o dists/stable/Release.gpg dists/stable/Release

git add .
git commit -m "APT auto-update for $VERSION" || true
git push

cd -

echo "== BUILD COMPLETE =="
ls -lh dist
