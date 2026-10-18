# frame-vitals-osc

Steam Frame の **バッテリー残量・充電中かどうか・SoC（CPU/GPU）温度** を、VRChat に OSC で送る小さな常駐ツールです。
アバターに「ヘッドセットの電池メーター」や「熱くなると汗をかく」ような演出を付けるために使えます。

- 依存なし: Steam Frame の SteamOS に最初から入っている Python 3 の標準ライブラリだけで動きます
- sudo 不要: すべてホームフォルダの中に入り、読むのは `/sys` の値だけです
- SteamVR・Steam・PipeWire などは一切再起動しません

## 送るもの

| OSC アドレス | 型 | 中身 |
|---|---|---|
| `/avatar/parameters/FrameBattery` | float 0.0〜1.0 | ヘッドセットのバッテリー残量（73% なら 0.73） |
| `/avatar/parameters/FrameTemp` | float 0.0〜1.0 | SoC のいちばん熱いゾーンの温度を正規化した値。既定では 30 °C → 0.0、95 °C → 1.0 |
| `/avatar/parameters/FrameCharging` | bool | 充電中（または満充電でつながっている）なら true |
| `/chatbox/input`（任意・既定オフ） | string, bool, bool | 例: `Frame 🔋73% ⚡ 🌡48°C`。最短 10 秒おき、通知音なし |

- 値は 2 秒ごとに読み、変わったときと、変わらなくても 10 秒ごとに送ります（VRChat 側でアバターを切り替えても値が戻るように）。
- パラメーター名は設定で変えられます。アバター側に同じ名前のパラメーターを用意してください（無ければ VRChat は無視するだけです）。
- フレームレート（fps）は今は送りません。SteamVR から安く取る方法が無いためです（frame-perf-overlay は OpenVR 経由で取得しています）。

### 値の出どころ（Steam Frame で確認）

- バッテリー: `/sys/class/power_supply/` の中で `type` が `Battery` のもの（Frame では `max1720x_bat_*`）の `capacity` と `status`
- 温度: `/sys/class/thermal/thermal_zone*/` のうち `type` が `cpu*` / `cpuss*` / `gpuss*` のゾーンの最大値

## 送り先

既定（`"host": "auto"`）では、[frameeyeosc](https://github.com/sasaken1102r/frameeyeosc) と同じ送り先を使います。

1. `~/.config/frameeyeosc/env` の `FRAMEEYEOSC_ARGS` に `--target ホスト:ポート` があればそれ
2. 無ければ `~/.config/frameeyeosc/config.json` の `host` / `port`（`auto` 以外のとき）
3. どちらも無ければ `127.0.0.1:9000`

VRChat を PC で動かして Steam Link で Frame につないでいる場合は、PC の LAN 内 IP（例: `192.168.1.10`）のポート 9000 になります。
`config.json` の `host` / `port` か、`--target 192.168.1.10:9000` で直接指定もできます。

## インストール

Frame の上で、ふつうのユーザーで:

```sh
git clone <このリポジトリ> /tmp/frame-vitals-osc
/tmp/frame-vitals-osc/install.sh
```

`~/.local/opt/frame-vitals-osc/` にスクリプトと `config.json`（無いときだけ例からコピー）が入り、
`~/.config/systemd/user/frame-vitals-osc.service` が置かれます。**自動起動は有効にしません。**

## 使い方

```sh
# 手動で試す（Ctrl+C で終了）。-v で送るたびに表示
python3 ~/.local/opt/frame-vitals-osc/frame-vitals-osc.py -v

# 送らずに、何を送るかだけ見る
python3 ~/.local/opt/frame-vitals-osc/frame-vitals-osc.py --once --dry-run

# サービスとして今だけ起動 / 止める
systemctl --user start frame-vitals-osc
systemctl --user stop frame-vitals-osc

# SteamVR と一緒に自動で起動する（次の SteamVR 起動から）/ やめる
systemctl --user enable frame-vitals-osc
systemctl --user disable --now frame-vitals-osc

# ログ
journalctl --user -u frame-vitals-osc -f
```

オプション: `--config FILE` / `--target host:port` / `--once` / `--dry-run` / `--duration 秒` / `--chatbox` / `-v` / `--version`

## 設定（`~/.local/opt/frame-vitals-osc/config.json`）

[`config.example.json`](config.example.json) に全項目の既定値があります。書かなかったキーは既定値になります。
設定は起動時に読むので、変えたら `systemctl --user restart frame-vitals-osc`（このツールだけの再起動です）。

| キー | 既定 | 意味 |
|---|---|---|
| `host` / `port` | `auto` / 9000 | 送り先。`auto` は frameeyeosc と同じ |
| `interval_s` | 2.0 | 値を読む間隔（秒） |
| `keepalive_s` | 10.0 | 変化がなくても送り直す間隔（秒） |
| `temp_min_c` / `temp_max_c` | 30 / 95 | FrameTemp が 0.0 / 1.0 になる温度 |
| `param_battery` など | `FrameBattery` など | アバターパラメーター名 |
| `chatbox` | false | チャットボックスに表示するか |
| `chatbox_interval_s` | 10.0 | チャットボックスの間隔（10 秒未満は 10 秒になる） |
| `chatbox_format` | `Frame 🔋{battery}%{charging} 🌡{temp:.0f}°C` | 表示の書式 |

## テスト

```sh
python3 tests/test_frame_vitals_osc.py                     # OSC エンコードの単体テストと localhost 送受信テスト
python3 tests/test_frame_vitals_osc.py --listen 19000 --seconds 60   # 受信して中身を表示（別端末で --target 127.0.0.1:19000）
```

## アンインストール

```sh
systemctl --user disable --now frame-vitals-osc
# あとは ~/.config/systemd/user/frame-vitals-osc.service と ~/.local/opt/frame-vitals-osc を片付ける
systemctl --user daemon-reload
```

## ライセンス

MIT
