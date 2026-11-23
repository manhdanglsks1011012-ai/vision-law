#!/bin/sh
# Run in a Python environment with PyQt6 and requirements-build.txt installed.
set -eu
task_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$task_root"
mkdir -p release
python3 -m PyInstaller --noconfirm --clean --onedir --name vision-law \
  --add-data assets:assets --hidden-import PyQt6.QtSvg \
  --exclude-module tkinter --exclude-module unittest \
  --distpath build-dist --workpath build-work launch.py
python3 packaging/build_release.py
python3 packaging/verify_release.py
