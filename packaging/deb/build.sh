#!/usr/bin/env bash
set -euo pipefail

VERSION="$1"

ROOT=/build
WORK=/tmp/simplytoast
OUT=/out

rm -rf "$WORK"
mkdir -p "$WORK/DEBIAN"
mkdir -p "$WORK/usr/lib/simplytoast"
mkdir -p "$WORK/usr/bin"
mkdir -p "$WORK/usr/share/applications"
mkdir -p "$WORK/usr/share/metainfo"
mkdir -p "$WORK/usr/share/icons/hicolor/512x512/apps"

# Extract artifact
tar -xzf "$ROOT/artifact.tar.gz" -C "$WORK/usr/lib/simplytoast"

# Control file (inject version)
sed "s/^Version:.*/Version: $VERSION/" "$ROOT/control" > "$WORK/DEBIAN/control"

# Postinst
install -m 755 "$ROOT/postinst" "$WORK/DEBIAN/postinst"

# Launcher wrapper
cat > "$WORK/usr/bin/simplytoast" <<'LAUNCHER'
#!/usr/bin/env bash
export PYTHONPATH="/usr/lib/simplytoast${PYTHONPATH:+:$PYTHONPATH}"
exec python3 /usr/lib/simplytoast/src/main.py "$@"
LAUNCHER
chmod 755 "$WORK/usr/bin/simplytoast"

# Desktop + metadata
install -m 644 "$WORK/usr/lib/simplytoast/data/com.toast1599.SimplyToast.desktop" \
  "$WORK/usr/share/applications/com.toast1599.SimplyToast.desktop"

install -m 644 "$WORK/usr/lib/simplytoast/data/com.toast1599.SimplyToast.appdata.xml" \
  "$WORK/usr/share/metainfo/com.toast1599.SimplyToast.appdata.xml"

install -m 644 "$WORK/usr/lib/simplytoast/data/icons/com.toast1599.SimplyToast-512.png" \
  "$WORK/usr/share/icons/hicolor/512x512/apps/com.toast1599.SimplyToast.png"

# Build .deb
dpkg-deb --build "$WORK" \
  "$OUT/simplytoast_${VERSION}_all.deb"
