#!/bin/bash
set -e

VERSION="$1"

if [ -z "$VERSION" ]; then
    echo "Please enter a version, like: ./release.sh 0.9.2"
    exit 1
fi

# Build DEB + AppImage
./build_all.sh "$VERSION"

# Commit + tag safely
git add .
git commit -m "Release v$VERSION" || true
git tag -f "v$VERSION"
git push
git push -f origin "v$VERSION"

# Create GitHub release
gh release create "v$VERSION" dist/* \
    --title "SimplyToast $VERSION" \
    --notes "Automatic release for version $VERSION"
