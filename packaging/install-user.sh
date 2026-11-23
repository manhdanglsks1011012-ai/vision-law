#!/bin/sh
set -eu
task_source=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
task_base=${XDG_DATA_HOME:-"$HOME/.local/share"}/vision-law
task_apps=${XDG_DATA_HOME:-"$HOME/.local/share"}/applications
task_version=1.0.0
mkdir -p "$task_base/releases" "$task_apps"
task_incoming=$(mktemp -d "$task_base/releases/.incoming.XXXXXX")
trap 'test ! -d "$task_incoming" || rm -rf -- "$task_incoming"' EXIT HUP INT TERM
cp -a "$task_source/app/." "$task_incoming/"
if [ -e "$task_base/releases/$task_version" ]; then
    mv -- "$task_base/releases/$task_version" "$task_base/releases/$task_version.previous.$(date +%Y%m%d%H%M%S)"
fi
mv -- "$task_incoming" "$task_base/releases/$task_version"
if [ -e "$task_base/current" ] && [ ! -L "$task_base/current" ]; then
    echo 'Không thay thế current vì đây không phải liên kết do trình cài tạo.' >&2
    exit 1
fi
ln -sfn -- "$task_base/releases/$task_version" "$task_base/current"
if [ -f "$task_apps/vision-law.desktop" ]; then
    cp -p -- "$task_apps/vision-law.desktop" "$task_base/launcher-before-$task_version.desktop"
fi
task_exe=$(printf '%s' "$task_base/current/vision-law" | sed 's/\\/\\\\/g;s/"/\\"/g;s/`/\\`/g;s/\$/\\$/g')
cat > "$task_apps/vision-law.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Vision law
Comment=Ghi chú và bo mạch kiến thức
Exec="$task_exe"
Icon=$task_base/current/_internal/assets/vision-law.svg
Terminal=false
Categories=Office;
StartupNotify=true
StartupWMClass=vision-law
EOF
chmod 644 "$task_apps/vision-law.desktop"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$task_apps" || true
fi
printf 'Đã cài Vision law %s. Mở Vision law từ menu ứng dụng.\n' "$task_version"
printf 'Ứng dụng: %s\n' "$task_base/current"
printf 'Vault và ghi chú hiện có không bị di chuyển.\n'
