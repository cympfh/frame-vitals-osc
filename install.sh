#!/bin/bash
# SPDX-License-Identifier: MIT
# frame-vitals-osc を ~/.local/opt/frame-vitals-osc に置き、systemd のユーザー unit を入れる。
# sudo 不要。unit は入れるだけで、有効化（自動起動）も起動もしない。SteamVR などは再起動しない。
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dest="$HOME/.local/opt/frame-vitals-osc"
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

mkdir -p "$dest" "$unit_dir"
if [[ "$here" != "$dest" ]]; then
    install -m755 "$here/frame-vitals-osc.py" "$dest/frame-vitals-osc.py"
    install -m644 "$here/config.example.json" "$dest/config.example.json"
fi
# 既存の config.json は上書きしない
[[ -f "$dest/config.json" ]] || install -m644 "$here/config.example.json" "$dest/config.json"
install -m644 "$here/contrib/frame-vitals-osc.service" "$unit_dir/frame-vitals-osc.service"
systemctl --user daemon-reload

cat <<MSG
frame-vitals-osc を入れました（有効化はしていません）。
  手動で試す:     python3 $dest/frame-vitals-osc.py -v
  今だけ起動:     systemctl --user start frame-vitals-osc
  自動起動オン:   systemctl --user enable frame-vitals-osc   （次の SteamVR 起動から一緒に動く）
  自動起動オフ:   systemctl --user disable --now frame-vitals-osc
  ログ:           journalctl --user -u frame-vitals-osc -f
MSG
