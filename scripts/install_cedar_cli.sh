#!/usr/bin/env bash
# Downloads the real Cedar policy-language CLI (cedar-policy/cedar on GitHub)
# to tools/cedar/cedar. Not vendored in git -- it's a ~15MB platform binary,
# so each dev/judge running this locally grabs their own copy. No AWS
# account, no login, just a public GitHub release download.
#
# The "cedar-policy" package on PyPI is an empty reserved placeholder (see
# IMPLEMENTATION.md) -- this is the actual authorization engine.
set -euo pipefail

VERSION="cedar-policy-cli-v4.13.0"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="$ROOT/tools/cedar"

os="$(uname -s)"
arch="$(uname -m)"
case "$os-$arch" in
  Darwin-arm64)  TARGET="aarch64-apple-darwin" ;;
  Darwin-x86_64) TARGET="x86_64-apple-darwin" ;;
  Linux-aarch64) TARGET="aarch64-unknown-linux-gnu" ;;
  Linux-x86_64)  TARGET="x86_64-unknown-linux-gnu" ;;
  *) echo "No prebuilt Cedar CLI for $os-$arch -- see https://github.com/cedar-policy/cedar/releases" >&2; exit 1 ;;
esac

ASSET="cedar-policy-cli-${TARGET}.tar.xz"
URL="https://github.com/cedar-policy/cedar/releases/download/${VERSION}/${ASSET}"

mkdir -p "$DEST_DIR"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Downloading $URL"
curl -sL -o "$TMP/cedar.tar.xz" "$URL"
tar -xJf "$TMP/cedar.tar.xz" -C "$TMP"
find "$TMP" -name cedar -type f -exec cp {} "$DEST_DIR/cedar" \;
chmod +x "$DEST_DIR/cedar"

"$DEST_DIR/cedar" --version
echo "Installed to $DEST_DIR/cedar"
