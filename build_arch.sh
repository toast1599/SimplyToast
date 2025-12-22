#!/usr/bin/env bash
set -euo pipefail

# ===============================
# STATE
# ===============================

COMMIT_CREATED=0
TAG_CREATED=0
TAG_PUSHED=0
ORIG_HEAD="$(git rev-parse HEAD)"

rollback() {
  echo "⚠️  ERROR — rolling back release"

  # remove pushed tag
  if [[ "$TAG_PUSHED" -eq 1 ]]; then
    echo "↩ Removing remote tag"
    git push origin ":refs/tags/$TAG" || true
  fi

  # remove local tag
  if [[ "$TAG_CREATED" -eq 1 ]]; then
    echo "↩ Removing local tag"
    git tag -d "$TAG" || true
  fi

  # reset commit + files
  if [[ "$COMMIT_CREATED" -eq 1 ]]; then
    echo "↩ Resetting git state"
    git reset --hard "$ORIG_HEAD" || true
  else
    git checkout -- .
  fi

  # clean build junk
  rm -rf pkg src/simplytoast-* *.pkg.tar.zst *.tar.gz PKGBUILD

  echo "❌ Rollback complete"
  exit 1
}

trap rollback ERR INT

# ===============================
# STEP 0: Args + sanity
# ===============================

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <version>"
  exit 1
fi

VERSION="$1"

if ! [[ "$VERSION" =~ ^[0-9]+(\.[0-9]+)*$ ]]; then
  echo "Invalid version format"
  exit 1
fi

TAG="v$VERSION"
TODAY="$(date +%Y-%m-%d)"

echo "▶ Releasing SimplyToast $VERSION"

# ===============================
# STEP 1: Git sanity
# ===============================

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "❌ Git tree is dirty"
  exit 1
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "❌ Tag already exists"
  exit 1
fi

# ===============================
# STEP 2: Update versioned files
# ===============================

cat > src/version.py <<EOF
VERSION = "$VERSION"
EOF

DESKTOP="data/com.toast1599.SimplyToast.desktop"
sed -i -E "s/^Version=.*/Version=$VERSION/" "$DESKTOP" \
  || echo "Version=$VERSION" >> "$DESKTOP"

APPDATA="data/com.toast1599.SimplyToast.appdata.xml"
sed -i "/<release version=\"$VERSION\"/d" "$APPDATA"
sed -i "/<releases>/a\\
    <release version=\"$VERSION\" date=\"$TODAY\"/>" "$APPDATA"

# ===============================
# STEP 3: Commit + tag
# ===============================

git add src/version.py "$DESKTOP" "$APPDATA"
git commit -m "Release $VERSION"
COMMIT_CREATED=1

git tag "$TAG"
TAG_CREATED=1

git push origin main
git push origin "$TAG"
TAG_PUSHED=1

# ===============================
# STEP 4: Arch build
# ===============================

PKGNAME=simplytoast
PKGREL=1
SRC_DIR="${PKGNAME}-${VERSION}"

rm -rf pkg src/$SRC_DIR *.pkg.tar.zst *.tar.gz PKGBUILD
mkdir -p src/$SRC_DIR

rsync -a \
  --exclude .git \
  --exclude pkg \
  --exclude "*.pkg.tar.zst" \
  --exclude "*.tar.gz" \
  ./ src/$SRC_DIR/

tar -czf "${SRC_DIR}.tar.gz" -C src "$SRC_DIR"

cat > PKGBUILD <<EOF
pkgname=${PKGNAME}
pkgver=${VERSION}
pkgrel=${PKGREL}
pkgdesc="GTK4 utility to manage startup and background applications"
arch=(any)
url="https://github.com/toast1599/SimplyToast"
license=(MIT)
depends=(python gtk4 python-gobject)
source=("${SRC_DIR}.tar.gz")
sha256sums=('SKIP')

package() {
  cd "${SRC_DIR}"

  install -Dm755 src/main.py \
    "\$pkgdir/usr/bin/simplytoast"

  install -Dm644 data/com.toast1599.SimplyToast.desktop \
    "\$pkgdir/usr/share/applications/com.toast1599.SimplyToast.desktop"

  install -Dm644 data/com.toast1599.SimplyToast.appdata.xml \
    "\$pkgdir/usr/share/metainfo/com.toast1599.SimplyToast.appdata.xml"

  install -Dm644 data/icons/com.toast1599.SimplyToast-512.png \
    "\$pkgdir/usr/share/icons/hicolor/512x512/apps/com.toast1599.SimplyToast.png"

  mkdir -p "\$pkgdir/usr/lib/simplytoast"
  cp -r src/app "\$pkgdir/usr/lib/simplytoast/"
  cp -r data "\$pkgdir/usr/lib/simplytoast/"
}
EOF

makepkg -sf

# ===============================
# SUCCESS
# ===============================

trap - ERR INT
echo "✅ Release $TAG completed successfully"
ls -1 *.pkg.tar.zst
