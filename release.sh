#!/usr/bin/env bash
set -euo pipefail

### -------------------------
### CONFIG
### -------------------------
APP_NAME="SimplyToast"
PKG_NAME="simplytoast"
TAG_PREFIX="v"

ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$ROOT/build"
OUT_DIR="$ROOT/out"

ARCH_PKG_DIR="$ROOT/packaging/arch"
DEB_PKG_DIR="$ROOT/packaging/deb"
RPM_PKG_DIR="$ROOT/packaging/rpm"
APPIMAGE_PKG_DIR="$ROOT/packaging/appimage"

### -------------------------
### ARGUMENTS
### -------------------------
VERSION="${1:-}"

if [[ -z "$VERSION" ]]; then
  echo "❌ Usage: ./release.sh <version>"
  exit 1
fi

if ! [[ "$VERSION" =~ ^[0-9]+(\.[0-9]+)+$ ]]; then
  echo "❌ Invalid version format: $VERSION"
  exit 1
fi

TAG="${TAG_PREFIX}${VERSION}"

### -------------------------
### PREFLIGHT CHECKS
### -------------------------
echo "▶ Releasing $APP_NAME $VERSION"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "❌ Git tree is dirty. Commit or stash changes first."
  exit 1
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "❌ Git tag $TAG already exists"
  exit 1
fi

command -v podman >/dev/null || { echo "❌ podman not installed"; exit 1; }
command -v gh >/dev/null || { echo "❌ gh not installed"; exit 1; }

### -------------------------
### CLEAN BUILD OUTPUT
### -------------------------
rm -rf "$BUILD_DIR" "$OUT_DIR"
mkdir -p "$BUILD_DIR" "$OUT_DIR"

### -------------------------
### VERSION BUMP (SOURCE OF TRUTH)
### -------------------------
echo "▶ Updating version.py"

cat > "$ROOT/src/version.py" <<EOF
VERSION = "$VERSION"
EOF

git add src/version.py
git commit -m "Bump version to $VERSION"

### -------------------------
### BUILD ARTIFACT (ONCE)
### -------------------------
echo "▶ Building artifact"

mkdir -p "$BUILD_DIR/artifact"

rsync -a \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  src/ "$BUILD_DIR/artifact/src/"

rsync -a data/ "$BUILD_DIR/artifact/data/"

tar -czf "$BUILD_DIR/artifact.tar.gz" -C "$BUILD_DIR/artifact" .

### -------------------------
### ARCH PACKAGE (HOST)
### -------------------------
echo "▶ Building Arch package"

cp "$BUILD_DIR/artifact.tar.gz" "$ARCH_PKG_DIR/"
(
  cd "$ARCH_PKG_DIR"
  makepkg -sf --noconfirm
  mv *.pkg.tar.zst "$OUT_DIR/"
)

### -------------------------
### DEB PACKAGE (CONTAINER)
### -------------------------
echo "▶ Building DEB package"

mkdir -p "$BUILD_DIR/deb"

cp "$BUILD_DIR/artifact.tar.gz" "$BUILD_DIR/deb/"
podman run --rm \
  -v "$BUILD_DIR/deb:/build:Z" \
  -v "$OUT_DIR:/out:Z" \
  simplytoast-deb \
  ./build.sh "$VERSION"

### -------------------------
### RPM PACKAGE (CONTAINER)
### -------------------------
echo "▶ Building RPM package"

mkdir -p "$BUILD_DIR/rpm"

cp "$BUILD_DIR/artifact.tar.gz" "$BUILD_DIR/rpm/"
podman run --rm \
  -v "$BUILD_DIR/rpm:/build:Z" \
  -v "$OUT_DIR:/out:Z" \
  simplytoast-rpm \
  ./build.sh "$VERSION"

### -------------------------
### APPIMAGE (CONTAINER)
### -------------------------
echo "▶ Building AppImage"

mkdir -p "$BUILD_DIR/appimage"

cp "$BUILD_DIR/artifact.tar.gz" "$BUILD_DIR/appimage/"
podman run --rm \
  -v "$BUILD_DIR/appimage:/build:Z" \
  -v "$OUT_DIR:/out:Z" \
  simplytoast-appimage \
  ./build.sh "$VERSION"

### -------------------------
### TAG + PUSH
### -------------------------
echo "▶ Tagging release $TAG"

git tag "$TAG"
git push origin main
git push origin "$TAG"

### -------------------------
### GITHUB RELEASE
### -------------------------
echo "▶ Creating GitHub release"

gh release create "$TAG" "$OUT_DIR"/* \
  --title "$APP_NAME $VERSION" \
  --notes "Automated release for $APP_NAME $VERSION"

echo "✅ Release $VERSION completed successfully"
