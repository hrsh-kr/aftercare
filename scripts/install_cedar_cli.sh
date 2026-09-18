#!/usr/bin/env bash
# Downloads the real Cedar policy-language CLI (cedar-policy/cedar on
# GitHub). Not vendored in git -- these are platform binaries, so each
# dev/judge running this locally grabs their own copy. No AWS account,
# no login, just a public GitHub release download.
#
# The "cedar-policy" package on PyPI is an empty reserved placeholder (see
# IMPLEMENTATION.md) -- this is the actual authorization engine.
#
# Fetches two binaries:
#   tools/cedar/cedar         -- host-native, used by the Flask dev server
#   tools/cedar-lambda/cedar  -- linux/aarch64, bundled into the SAM Local
#                                 Lambda package so `cedar authorize` can
#                                 actually run inside that container (a
#                                 macOS binary can't execute in a Lambda's
#                                 Amazon Linux runtime)
set -euo pipefail

VERSION="cedar-policy-cli-v4.13.0"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

download() {
  local target="$1" dest_dir="$2"
  local asset="cedar-policy-cli-${target}.tar.xz"
  local url="https://github.com/cedar-policy/cedar/releases/download/${VERSION}/${asset}"
  local tmp
  tmp="$(mktemp -d)"
  echo "Downloading $url"
  curl -sL -o "$tmp/cedar.tar.xz" "$url"
  tar -xJf "$tmp/cedar.tar.xz" -C "$tmp"
  mkdir -p "$dest_dir"
  find "$tmp" -name cedar -type f -exec cp {} "$dest_dir/cedar" \;
  chmod +x "$dest_dir/cedar"
  rm -rf "$tmp"
  echo "Installed to $dest_dir/cedar"
}

os="$(uname -s)"
arch="$(uname -m)"
case "$os-$arch" in
  Darwin-arm64)  HOST_TARGET="aarch64-apple-darwin" ;;
  Darwin-x86_64) HOST_TARGET="x86_64-apple-darwin" ;;
  Linux-aarch64) HOST_TARGET="aarch64-unknown-linux-gnu" ;;
  Linux-x86_64)  HOST_TARGET="x86_64-unknown-linux-gnu" ;;
  *) echo "No prebuilt Cedar CLI for $os-$arch -- see https://github.com/cedar-policy/cedar/releases" >&2; exit 1 ;;
esac

download "$HOST_TARGET" "$ROOT/tools/cedar"
"$ROOT/tools/cedar/cedar" --version

download "aarch64-unknown-linux-gnu" "$ROOT/tools/cedar-lambda"
echo "(Lambda copy is linux/aarch64 -- won't run on this host, that's expected; it runs inside SAM Local's container.)"
