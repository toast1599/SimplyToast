#!/usr/bin/env bash
set -euo pipefail

VERSION="$1"

ROOT=/build
OUT=/out
RPMBUILD=/tmp/rpmbuild

mkdir -p "$RPMBUILD"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

cp "$ROOT/artifact.tar.gz" "$RPMBUILD/SOURCES/"

sed "s/^Version:.*/Version:        $VERSION/" \
  "$ROOT/simplytoast.spec" > "$RPMBUILD/SPECS/simplytoast.spec"

rpmbuild \
  --define "_topdir $RPMBUILD" \
  -ba "$RPMBUILD/SPECS/simplytoast.spec"

# ✅ FIXED LINE
cp "$RPMBUILD/RPMS/"*/*.rpm "$OUT/"
