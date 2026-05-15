#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd)"
URL="https://github.com/uw-pluverse/perses/releases/download/v2.5/perses_deploy.jar"
DEST="$ROOT/perses/perses_deploy.jar"

mkdir -p "$ROOT/perses"

tmp="$(mktemp "$DEST.tmp.XXXXXX")"
cleanup() {
  rm -f "$tmp"
}
trap cleanup EXIT

if command -v curl >/dev/null 2>&1; then
  curl -L --fail -o "$tmp" "$URL"
elif command -v wget >/dev/null 2>&1; then
  wget -O "$tmp" "$URL"
else
  echo "curl or wget is required to download Perses" >&2
  exit 1
fi

mv "$tmp" "$DEST"
trap - EXIT

echo "Installed Perses to $DEST"
