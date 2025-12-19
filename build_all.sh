#!/usr/bin/env bash
set -euo pipefail

# ===============================
# STEP 0: Args + version authority
# ===============================

if [[ $# -ne 1 ]]; then
  echo "❌ Usage: ./build_all.sh <version>"
  exit 1
fi

VERSION="$1"

if ! [[ "$VERSION" =~ ^[0-9]+(\.[0-9]+)*$ ]]; then
  echo "❌ Invalid version format: $VERSION"
  exit 1
fi

TAG="v$VERSION"
TAG_CREATED=0

cleanup_tag() {
  if [[ "$TAG_CREATED" -eq 1 ]]; then
    echo "⚠️ Cleaning up failed release tag $TAG"
    git tag -d "$TAG" 2>/dev/null || true
    git push origin ":refs/tags/$TAG" 2>/dev/null || true
  fi
}

trap cleanup_tag ERR

echo "▶ Building SimplyToast version: $VERSION"

# ===============================
# STEP 1: Update version.py
# ===============================

VERSION_FILE="src/version.py"

cat > "$VERSION_FILE" <<EOF
VERSION = "$VERSION"
EOF

# ===============================
# STEP 2: Desktop + AppStream
# ===============================

DESKTOP_FILE="data/com.toast1599.SimplyToast.desktop"
APPDATA_FILE="data/com.toast1599.SimplyToast.appdata.xml"
TODAY="$(date +%Y-%m-%d)"

sed -i -E "s/^Version=.*/Version=$VERSION/" "$DESKTOP_FILE" \
  || echo "Version=$VERSION" >> "$DESKTOP_FILE"

sed -i "/<release version=\"$VERSION\"/d" "$APPDATA_FILE"
sed -i "/<releases>/a\\
    <release version=\"$VERSION\" date=\"$TODAY\"/>" "$APPDATA_FILE"

# ===============================
# STEP 3: RPM build
# ===============================

RPMBUILD="$HOME/rpmbuild"
mkdir -p "$RPMBUILD"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

PKG_NAME="simplytoast"
TARBALL="$RPMBUILD/SOURCES/${PKG_NAME}-${VERSION}.tar.gz"

TMP_SRC_DIR="$(mktemp -d)"
PKG_SRC_DIR="$TMP_SRC_DIR/${PKG_NAME}-${VERSION}"

rsync -a \
  --exclude=".git" \
  --exclude="AppDir" \
  --exclude="flatpak-repo" \
  --exclude="build_all.sh" \
  ./ "$PKG_SRC_DIR/"

tar -czf "$TARBALL" -C "$TMP_SRC_DIR" "${PKG_NAME}-${VERSION}"
rm -rf "$TMP_SRC_DIR"

SPEC_FILE="$RPMBUILD/SPECS/simplytoast.spec"

cat > "$SPEC_FILE" <<EOF
Name: simplytoast
Version: $VERSION
Release: 1%{?dist}
Summary: Manage startup and background applications
License: GPL-3.0-or-later
URL: https://github.com/toast1599/SimplyToast
Source0: %{name}-%{version}.tar.gz
BuildArch: noarch
Requires: python3, python3-gobject, gtk4

%description
SimplyToast is a GTK4 utility for managing startup applications.

%prep
%autosetup -n %{name}-%{version}

%install
mkdir -p %{buildroot}/usr/libexec/simplytoast
cp -r src data %{buildroot}/usr/libexec/simplytoast

mkdir -p %{buildroot}/usr/bin
printf '#!/bin/sh\nexec /usr/bin/python3 /usr/libexec/simplytoast/src/main.py "\$@"\n' \
  > %{buildroot}/usr/bin/simplytoast
chmod 755 %{buildroot}/usr/bin/simplytoast

mkdir -p %{buildroot}/usr/share/applications
install -m 644 data/com.toast1599.SimplyToast.desktop \
  %{buildroot}/usr/share/applications/com.toast1599.SimplyToast.desktop

mkdir -p %{buildroot}/usr/share/metainfo
install -m 644 data/com.toast1599.SimplyToast.appdata.xml \
  %{buildroot}/usr/share/metainfo/com.toast1599.SimplyToast.appdata.xml

mkdir -p %{buildroot}/usr/share/icons/hicolor/512x512/apps
install -m 644 data/icons/com.toast1599.SimplyToast-512.png \
  %{buildroot}/usr/share/icons/hicolor/512x512/apps/com.toast1599.SimplyToast.png

%files
/usr/bin/simplytoast
/usr/libexec/simplytoast
/usr/share/applications/*
/usr/share/metainfo/*
/usr/share/icons/hicolor/512x512/apps/*
EOF

rpmbuild --define "_topdir $RPMBUILD" -ba "$SPEC_FILE"

# ===============================
# STEP 4: Flatpak build
# ===============================

FLATPAK_ID="com.toast1599.SimplyToast"
FLATPAK_BUNDLE="SimplyToast-$VERSION.flatpak"

flatpak install -y flathub org.gnome.Platform//49 org.gnome.Sdk//49

flatpak-builder --force-clean --repo=flatpak-repo flatpak-build "$FLATPAK_ID.json"
flatpak build-bundle flatpak-repo "$FLATPAK_BUNDLE" "$FLATPAK_ID"

# ===============================
# STEP 5: Tag + GitHub Release
# ===============================

if command -v gh >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "▶ Creating git tag $TAG"

  if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "❌ Tag $TAG already exists"
    exit 1
  fi

  git tag "$TAG"
  git push origin "$TAG"
  TAG_CREATED=1

  gh release create "$TAG" \
    --title "SimplyToast $VERSION" \
    --notes "Release $VERSION"

  RPM_FILES=$(ls ~/rpmbuild/RPMS/**/*.rpm 2>/dev/null || true)

  gh release upload "$TAG" \
    $RPM_FILES \
    "$FLATPAK_BUNDLE" \
    --clobber
else
  echo "⚠️ gh or git unavailable — skipping release"
fi

trap - ERR
echo "✅ Release $TAG completed successfully"
