#!/usr/bin/env bash
set -euo pipefail

# build_all.sh - automated builder for SimplyToast
# Usage: ./build_all.sh <version> [--no-upload]
#
# - Builds .deb, AppImage, and Snap
# - Uploads snap to Snap Store (edge) and assets to GitHub release
# - Updates the local APT repo directory (must be a git repo you control)
#
# IMPORTANT:
# - Must run from project repo root.
# - Ensure you are logged in: `gh auth status` and `snapcraft login`
# - Ensure you have a GPG key named in GPG_KEY variable (or change it)
#
###############################################################################

VERSION="$1"
NO_UPLOAD="false"
if [ "${2:-}" = "--no-upload" ]; then
  NO_UPLOAD="true"
fi

# Config - edit if your layout differs
GPG_KEY="toast1599"
APT_REPO="/home/toast1599/simplytoast-apt"
SNAP_YAML="snap/snapcraft.yaml"
LINUXDEPLOY="./linuxdeploy-x86_64.AppImage"

if [ -z "$VERSION" ]; then
  echo "Usage: $0 <version> [--no-upload]"
  exit 1
fi

# Quick tool checks
required=(git dpkg-deb dpkg-scanpackages apt-ftparchive gpg gh snapcraft)
for cmd in "${required[@]}"; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[ERR] required command not found: $cmd"
    exit 1
  fi
done

if [ ! -x "$LINUXDEPLOY" ]; then
  echo "[WARN] linuxdeploy AppImage not found or not executable at $LINUXDEPLOY"
  echo "       AppImage build will fail if linuxdeploy is required."
fi

# Ensure running from repo root (where src/ and data/ exist)
if [ ! -d src ] || [ ! -d data ]; then
  echo "[ERR] Must be run from repository root (missing src/ or data/)"
  exit 1
fi

# Optional: allow running even with dirty tree with env flag, otherwise require clean
if [ -n "$(git status --porcelain)" ]; then
  echo "[ERR] Git working tree is dirty. Commit or stash changes before running this script."
  git status --short
  exit 1
fi

echo "[*] Starting build pipeline for SimplyToast v$VERSION"

# Make a clean dist folder
rm -rf dist
mkdir -p dist

# ---------- 1) Build .deb ----------
echo "[1/4] Building DEB..."
TMP_DEB="deb_build"
rm -rf "$TMP_DEB"
mkdir -p "$TMP_DEB"/{usr/bin,usr/share/simplytoast,usr/share/applications,usr/share/icons/hicolor/512x512/apps,DEBIAN,usr/share/metainfo}

# Ensure executable and correct permissions
install -Dm755 src/main.py "$TMP_DEB/usr/bin/simplytoast"
cp -r assets data "$TMP_DEB/usr/share/simplytoast/"
cp data/com.toast1599.SimplyToast.desktop "$TMP_DEB/usr/share/applications/"
cp data/com.toast1599.SimplyToast.png "$TMP_DEB/usr/share/icons/hicolor/512x512/apps/"
cp data/com.toast1599.SimplyToast.appdata.xml "$TMP_DEB/usr/share/metainfo/" || true

cat > "$TMP_DEB/DEBIAN/control" <<EOF
Package: simplytoast
Version: $VERSION
Architecture: all
Maintainer: toast1599
Description: Startup application manager
EOF

# build
dpkg-deb --build "$TMP_DEB" "dist/simplytoast_${VERSION}.deb"
echo "[1/4] DEB built: dist/simplytoast_${VERSION}.deb"

# ---------- 2) Build AppImage ----------
echo "[2/4] Building AppImage..."
TMP_APPDIR="AppDir"
rm -rf "$TMP_APPDIR"
mkdir -p "$TMP_APPDIR"/{usr/bin,usr/share/simplytoast,usr/share/applications,usr/share/icons/hicolor/512x512/apps,usr/share/metainfo}

install -Dm755 src/main.py "$TMP_APPDIR/usr/bin/simplytoast"
cp -r assets data "$TMP_APPDIR/usr/share/simplytoast/"
cp data/com.toast1599.SimplyToast.desktop "$TMP_APPDIR/usr/share/applications/"
cp data/com.toast1599.SimplyToast.png "$TMP_APPDIR/usr/share/icons/hicolor/512x512/apps/"
cp data/com.toast1599.SimplyToast.appdata.xml "$TMP_APPDIR/usr/share/metainfo/" || true

if [ -x "$LINUXDEPLOY" ]; then
  ARCH=x86_64 "$LINUXDEPLOY" --appdir "$TMP_APPDIR" --output appimage
  APPIMAGE_FILE=$(ls SimplyToast-*.AppImage 2>/dev/null || true)
  if [ -z "$APPIMAGE_FILE" ]; then
    echo "[WARN] AppImage not created by linuxdeploy. Check linuxdeploy output."
  else
    mv "$APPIMAGE_FILE" "dist/SimplyToast-${VERSION}.AppImage"
    echo "[2/4] AppImage built: dist/SimplyToast-${VERSION}.AppImage"
  fi
else
  echo "[WARN] Skipping AppImage creation because linuxdeploy not available/executable."
fi

# ---------- 3) Build SNAP (in clean temp dir to avoid dump plugin hardlink issues) ----------
echo "[3/4] Building SNAP..."

if [ ! -f "$SNAP_YAML" ]; then
  echo "[WARN] $SNAP_YAML not found. Skipping snap build."
else
  TMP_SNAPDIR=$(mktemp -d)
  echo "[3/4] Using temporary snap build dir: $TMP_SNAPDIR"

  # copy only the files snap needs (avoid copying .git and huge build artifacts)
  mkdir -p "$TMP_SNAPDIR"
  cp "$SNAP_YAML" "$TMP_SNAPDIR/snapcraft.yaml"

  # copy src, data, assets, and any desktop/icon referenced
  mkdir -p "$TMP_SNAPDIR/src" "$TMP_SNAPDIR/data" "$TMP_SNAPDIR/assets"
  cp -a src/main.py "$TMP_SNAPDIR/src/"
  cp -a data/* "$TMP_SNAPDIR/data/" || true
  cp -a assets/* "$TMP_SNAPDIR/assets/" || true

  # Update version in the temporary snapcraft.yaml safely (preserve original)
  sed -E "s/^version: .*/version: '$VERSION'/" "$TMP_SNAPDIR/snapcraft.yaml" > "$TMP_SNAPDIR/snapcraft.yaml.tmp" && mv "$TMP_SNAPDIR/snapcraft.yaml.tmp" "$TMP_SNAPDIR/snapcraft.yaml"

  # Ensure correct permissions for executable and world-readable
  chmod 755 "$TMP_SNAPDIR/src/main.py"
  # make sure icons and desktop are readable
  chmod -R a+r "$TMP_SNAPDIR/data" "$TMP_SNAPDIR/assets" || true

  pushd "$TMP_SNAPDIR" >/dev/null

  # Choose snapcraft mode: prefer LXD if available and usable
  if snap list lxd >/dev/null 2>&1 && lxc list >/dev/null 2>&1; then
    echo "[3/4] Building snap with LXD"
    snapcraft --use-lxd || { echo "[ERR] snapcraft (LXD) failed"; popd >/dev/null; rm -rf "$TMP_SNAPDIR"; exit 1; }
  else
    echo "[3/4] Building snap with destructive-mode (no LXD)"
    snapcraft --destructive-mode || { echo "[ERR] snapcraft (destructive) failed"; popd >/dev/null; rm -rf "$TMP_SNAPDIR"; exit 1; }
  fi

  # find produced snap and move to dist
  SNAP_PROD=$(ls *.snap 2>/dev/null | grep simplytoast || true)
  if [ -n "$SNAP_PROD" ]; then
    mv "$SNAP_PROD" "$OLDPWD/dist/simplytoast_${VERSION}_amd64.snap"
    echo "[3/4] Snap built: dist/simplytoast_${VERSION}_amd64.snap"
  else
    echo "[WARN] No snap artifact found after build."
  fi

  popd >/dev/null
  rm -rf "$TMP_SNAPDIR"
fi

# ---------- 4) Uploads ----------
if [ "$NO_UPLOAD" = "true" ]; then
  echo "[UPLOAD] Skipping uploads (--no-upload)."
else
  # Snap upload
  if [ -f "dist/simplytoast_${VERSION}_amd64.snap" ]; then
    echo "[4/4] Uploading snap to snap store (edge)..."
    if snapcraft upload "dist/simplytoast_${VERSION}_amd64.snap" --release=edge; then
      echo "[SNAPSTORE] Snap uploaded and released to 'edge'."
    else
      echo "[SNAPSTORE] Upload failed. Run 'snapcraft login' or check snapcraft status."
      exit 1
    fi
  else
    echo "[SNAPSTORE] No snap artifact to upload, skipping."
  fi

  # GitHub release upload
  echo "[GITHUB] Creating GitHub release v$VERSION (will overwrite if exists)..."
  if gh release view "v$VERSION" >/dev/null 2>&1; then
    gh release delete "v$VERSION" --yes || true
    git tag -d "v$VERSION" || true
  fi

  git tag "v$VERSION"
  git push origin "v$VERSION"

  # create a release and upload assets
  gh release create "v$VERSION" dist/* \
    --title "SimplyToast v$VERSION" \
    --notes "Automated release for version $VERSION"

  echo "[GITHUB] Release created and assets uploaded."
fi

# ---------- 5) Update local APT repo ----------
if [ -d "$APT_REPO" ]; then
  echo "[APT] Updating APT repo at $APT_REPO"
  cp "dist/simplytoast_${VERSION}.deb" "$APT_REPO/pool/main/s/" || { echo "[APT] Failed to copy deb to pool"; exit 1; }

  pushd "$APT_REPO" >/dev/null

  # regenerate Packages files
  dpkg-scanpackages pool /dev/null > Packages
  gzip -9c Packages > Packages.gz

  mkdir -p dists/stable
  cp Packages dists/stable/Packages
  cp Packages.gz dists/stable/Packages.gz

  # generate Release
  apt-ftparchive release dists/stable > dists/stable/Release

  # sign Release (requires GPG key available locally)
  if gpg --list-keys "$GPG_KEY" >/dev/null 2>&1; then
    gpg --batch --yes --default-key "$GPG_KEY" --clearsign -o dists/stable/InRelease dists/stable/Release
    gpg --batch --yes --default-key "$GPG_KEY" -abs -o dists/stable/Release.gpg dists/stable/Release
    echo "[APT] Signed InRelease and Release.gpg with $GPG_KEY"
  else
    echo "[APT] WARNING: GPG key $GPG_KEY not found locally. Release files left unsigned."
  fi

  git add .
  git commit -m "APT auto-update for $VERSION" || true
  git push || echo "[APT] Warning: git push failed. Check remote."

  popd >/dev/null
else
  echo "[APT] APT repository path $APT_REPO not found; skipping APT update."
fi

echo "== BUILD COMPLETE =="
ls -lh dist || true
