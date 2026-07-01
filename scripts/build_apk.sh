#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${HOME}/film-border-build"
OUTPUT_DIR="${PROJECT_DIR}/bin"

export PATH="${HOME}/.local/bin:${PATH}"

if ! command -v buildozer >/dev/null 2>&1; then
  echo "Buildozer is not installed. Run this first inside WSL/Linux:" >&2
  echo "  bash scripts/setup_android_build_env.sh" >&2
  exit 1
fi

mkdir -p "${BUILD_DIR}" "${OUTPUT_DIR}"

echo "Syncing project to ASCII build path: ${BUILD_DIR}"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete \
    --exclude ".venv" \
    --exclude ".buildozer" \
    --exclude "__pycache__" \
    --exclude "exports" \
    --exclude "bin" \
    "${PROJECT_DIR}/" "${BUILD_DIR}/"
else
  rm -rf "${BUILD_DIR}"
  mkdir -p "${BUILD_DIR}"
  cp -R "${PROJECT_DIR}/." "${BUILD_DIR}/"
  rm -rf "${BUILD_DIR}/.venv" "${BUILD_DIR}/.buildozer" "${BUILD_DIR}/__pycache__" "${BUILD_DIR}/exports" "${BUILD_DIR}/bin"
fi

cd "${BUILD_DIR}"
echo "Building debug APK..."
buildozer -v android debug

mkdir -p "${OUTPUT_DIR}"
cp -f bin/*.apk "${OUTPUT_DIR}/"

echo
echo "APK copied to:"
ls -1 "${OUTPUT_DIR}"/*.apk

