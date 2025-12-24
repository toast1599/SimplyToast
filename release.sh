#!/usr/bin/env bash
set -euo pipefail

### -------------------------
### CONFIG & CLEANUP TRAP
### -------------------------
APP_NAME="SimplyToast"
TAG_PREFIX="v"

TAG_CREATED=0

ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$ROOT/build"
OUT_DIR="$ROOT/out"

# This function runs if the script exits UNEXPECTEDLY
cleanup_on_failure() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "⚠️ Script failed with exit code $exit_code. Cleaning up..."
        
        # 1. Remove build artifacts
        rm -rf "$BUILD_DIR" "$OUT_DIR"
        
        # 2. Rollback git changes (version.py bump)
        git reset --hard HEAD >/dev/null 2>&1
        
        # 3. Delete the tag if it was created locally but not pushed
        if [[ "$TAG_CREATED" -eq 1 ]]; then
            git tag -d "$TAG"
        fi
        
        echo "🧹 Environment restored to original state."
    fi
}

# Register the cleanup function to run on exit
trap cleanup_on_failure EXIT

### -------------------------
### ARGUMENTS & PREFLIGHT
### -------------------------
VERSION="${1:-}"
if [[ -z "$VERSION" || ! "$VERSION" =~ ^[0-9]+(\.[0-9]+)+$ ]]; then
  echo "❌ Usage: ./release.sh <version> (e.g. 1.2.3)"
  exit 1
fi

TAG="${TAG_PREFIX}${VERSION}"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [[ -n "$(git status --porcelain)" ]]; then
  echo "❌ Git tree is dirty. Commit or stash changes first."
  exit 1
fi

### -------------------------
### EXECUTION (VERSION BUMP)
### -------------------------
echo "▶ Updating version.py"
cat > "$ROOT/src/version.py" <<EOF
VERSION = "$VERSION"
EOF

git add src/version.py
if git diff --cached --quiet; then
  echo "ℹ️ version.py already at $VERSION"
else
  git commit -m "Bump version to $VERSION"
fi


### -------------------------
### BUILDING (STAYING CLEAN)
### -------------------------
mkdir -p "$BUILD_DIR" "$OUT_DIR"

echo "▶ Packing Source..."
mkdir -p "$BUILD_DIR/artifact"
rsync -a --exclude='__pycache__' --exclude='*.pyc' --exclude='*.AppImage' src/ "$BUILD_DIR/artifact/src/"
rsync -a data/ "$BUILD_DIR/artifact/data/"
tar -czf "$BUILD_DIR/artifact.tar.gz" -C "$BUILD_DIR/artifact" .

# --- ARCH ---
echo "▶ Building Arch..."
mkdir -p "$BUILD_DIR/arch"
cp "$ROOT/packaging/arch/PKGBUILD" "$BUILD_DIR/arch/"
cp "$BUILD_DIR/artifact.tar.gz" "$BUILD_DIR/arch/"
(cd "$BUILD_DIR/arch" && makepkg -sf --noconfirm && mv *.pkg.tar.zst "$OUT_DIR/")

# --- DEB ---
echo "▶ Building DEB..."
mkdir -p "$BUILD_DIR/deb"
cp -r "$ROOT/packaging/deb/"* "$BUILD_DIR/deb/"
cp "$BUILD_DIR/artifact.tar.gz" "$BUILD_DIR/deb/"
podman run --rm -v "$BUILD_DIR/deb:/build:Z" -v "$OUT_DIR:/out:Z" simplytoast-deb ./build.sh "$VERSION"

# --- RPM ---
echo "▶ Building RPM..."
mkdir -p "$BUILD_DIR/rpm"
cp -r "$ROOT/packaging/rpm/"* "$BUILD_DIR/rpm/"
cp "$BUILD_DIR/artifact.tar.gz" "$BUILD_DIR/rpm/"
podman run --rm -v "$BUILD_DIR/rpm:/build:Z" -v "$OUT_DIR:/out:Z" simplytoast-rpm ./build.sh "$VERSION"

# --- APPIMAGE ---
echo "▶ Building AppImage..."
mkdir -p "$BUILD_DIR/appimage"
cp -r "$ROOT/packaging/appimage/"* "$BUILD_DIR/appimage/"
cp "$BUILD_DIR/artifact.tar.gz" "$BUILD_DIR/appimage/"
podman run --rm -v "$BUILD_DIR/appimage:/build:Z" -v "$OUT_DIR:/out:Z" simplytoast-appimage ./build.sh "$VERSION"

### -------------------------
### THE FINAL PUSH
### -------------------------
echo "▶ Tagging and Pushing..."
git tag "$TAG"
TAG_CREATED=1
git push origin "$CURRENT_BRANCH"
git push origin "$TAG"

echo "▶ Creating GitHub release..."
gh release create "$TAG" "$OUT_DIR"/* --title "$APP_NAME $VERSION" --notes "Release $VERSION"

### -------------------------
### SUCCESS: DISARM CLEANUP
### -------------------------
# If we made it here, success! 
# We remove the trap so the files STAY for you to see.
trap - EXIT
echo "✅ Release $VERSION completed successfully. Artifacts are in $OUT_DIR"