#!/bin/bash
set -e

VERSION="$1"

if [ -z "$VERSION" ]; then
    echo "Please enter a version, like: ./release.sh 0.9.9"
    exit 1
fi

# Build everything
./build_all.sh "$VERSION"

# Build Arch package inside Docker
echo "== Building Arch package inside Docker =="

docker run --rm \
    -v "$(pwd)":/work \
    archlinux:latest bash -c "
        pacman -Sy --noconfirm base-devel git &&
        cd /work/pkgbuild &&
        makepkg -fs --noconfirm
    "

cp pkgbuild/*.pkg.tar.zst dist/

# Create GitHub release automatically
gh release create "v$VERSION" dist/* --title "SimplyToast $VERSION" --notes "Automatic release"
