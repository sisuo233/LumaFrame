#!/usr/bin/env bash
set -euo pipefail

echo "Installing Android build dependencies for Buildozer..."

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This script expects Ubuntu/Debian inside WSL or Linux." >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y \
  autoconf \
  automake \
  build-essential \
  ccache \
  cmake \
  git \
  libffi-dev \
  libltdl-dev \
  libssl-dev \
  libtool \
  openjdk-17-jdk \
  patch \
  pkg-config \
  python3 \
  python3-pip \
  python3-venv \
  unzip \
  zip \
  zlib1g-dev

python3 -m pip install --user --upgrade pip
python3 -m pip install --user --upgrade buildozer cython virtualenv

echo
echo "Done. If 'buildozer' is not found, run:"
echo '  export PATH="$HOME/.local/bin:$PATH"'

