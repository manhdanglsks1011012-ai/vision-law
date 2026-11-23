#!/bin/sh
set -eu
task_base=${XDG_DATA_HOME:-"$HOME/.local/share"}/vision-law
task_apps=${XDG_DATA_HOME:-"$HOME/.local/share"}/applications
if [ -f "$task_apps/vision-law.desktop" ] && grep -F "$task_base/current/vision-law" "$task_apps/vision-law.desktop" >/dev/null 2>&1; then
    rm -- "$task_apps/vision-law.desktop"
fi
if [ -L "$task_base/current" ]; then rm -- "$task_base/current"; fi
if [ -d "$task_base/releases" ]; then rm -rf -- "$task_base/releases"; fi
printf 'Đã gỡ phần chạy ứng dụng. Vault, ghi chú, cấu hình và bản nháp phục hồi được giữ nguyên.\n'
