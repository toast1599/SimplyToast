#!/bin/bash
set -e

VERSION="$1"

if [ -z "$VERSION" ]; then
    echo "Usage: ./build_all.sh <version>"
    echo "Example: ./build_all.sh 0.9.1.4"
    exit 1
fi

echo "== Building SimplyToast v$VERSION =="

rm -rf dist
mkdir dist

# -------------------------
# Build source tarball
# -------------------------
echo "[1/4] Building tar.gz..."
mkdir -p temp_src/SimplyToast-$VERSION
cp -r src assets data LICENSE README.md temp_src/SimplyToast-$VERSION/

tar czf dist/SimplyToast-$VERSION.tar.gz -C temp_src SimplyToast-$VERSION

rm -rf temp_src

# -------------------------
# Build .deb package
# -------------------------
echo "[2/4] Building DEB..."
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
echo "[3/4] Building AppImage..."
rm -rf AppDir
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/simplytoast
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/512x512/apps

install -Dm755 src/main.py AppDir/usr/bin/simplytoast
cp -r assets data AppDir/usr/share/simplytoast/
cp data/com.toast1599.SimplyToast.desktop AppDir/usr/share/applications/
cp data/com.toast1599.SimplyToast.png AppDir/usr/share/icons/hicolor/512x512/apps/

ARCH=x86_64 ./linuxdeploy-x86_64.AppImage --appdir AppDir --output appimage

APPIMAGE_FILE=$(ls SimplyToast-*.AppImage | head -n 1)
mv "$APPIMAGE_FILE" "dist/SimplyToast-$VERSION.AppImage"

# -------------------------
# Build Arch PKG in Docker
# -------------------------
echo "[4/4] Arch Linux PKG (inside Docker)..."

# auto-update PKGBUILD version
sed -i "s/^pkgver=.*/pkgver=$VERSION/" PKGBUILD
sed -i "s/^source=.*/source=(\"SimplyToast-$VERSION.tar.gz\")/" PKGBUILD

# prepare pkgbuild folder
rm -rf pkgbuild
mkdir pkgbuild
cp PKGBUILD pkgbuild/
cp dist/SimplyToast-$VERSION.tar.gz pkgbuild/

# run arch inside docker using NON-ROOT USER (builderr)
docker run --rm -t \
    -v "$(pwd)":/work \
    archlinux:latest \
    bash -c "
        set -e

        pacman -Sy --noconfirm base-devel git sudo

        # create normal build user
        useradd -m builderr
        echo 'builderr ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

        # fix perms so builderr can write to mounted folder
        chown -R builderr:builderr /work

        # build as non-root user
        sudo -u builderr bash -c '
            cd /work/pkgbuild
            makepkg -fs --noconfirm
        '
    "

# move package to dist
cp pkgbuild/*.pkg.tar.zst dist/

ls -lh dist
