#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "$0")"
exec python3 launch.py "${1:-$PWD/demo-vault}"
