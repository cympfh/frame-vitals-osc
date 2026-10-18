# 開発者向けメモ

## 送るもの

| OSC アドレス | 型 | 中身 |
|---|---|---|
| `/avatar/parameters/FrameBattery` | float 0〜1 | 電池残量 |
| `/avatar/parameters/FrameTemp` | float 0〜1 | SoC のいちばん熱いゾーンの温度（なめらかにしてから `temp_min_c`〜`temp_max_c` を 0〜1 に） |
| `/avatar/parameters/FrameCharging` | bool | 充電中（または満充電でつながっている） |
| `/chatbox/input`（既定オフ） | string, true, false | すぐ表示・通知音なし。10 秒に 1 回まで |

2 秒ごとに値を読み、変わったとき（温度は 1 °C 以上）と、変わらなくても 10 秒ごとに送ります。

値の出どころ: `/sys/class/power_supply/*`（`type` が `Battery` のもの）の `capacity` と `status`、
`/sys/class/thermal/thermal_zone*` のうち `cpu*` / `cpuss*` / `gpuss*` の最大値。

## 送り先

`"host": "auto"`（既定）のときは、frameeyeosc の `~/.config/frameeyeosc/env` の `--target`、
次に `~/.config/frameeyeosc/config.json` の `host` / `port`、どちらも無ければ `127.0.0.1:9000`。

## 設定（`~/.config/frame-vitals-osc/config.json`）

| 項目 | 既定 | 意味 |
|---|---|---|
| `host` / `port` | `auto` / 9000 | 送り先 |
| `interval_s` | 2.0 | 値を読む間隔（秒） |
| `keepalive_s` | 10.0 | 変化がなくても送り直す間隔（秒） |
| `temp_min_c` / `temp_max_c` | 30 / 95 | FrameTemp が 0 / 1 になる温度 |
| `temp_smoothing` | 0.3 | 温度をなめらかにする強さ（1 でそのまま） |
| `temp_change_c` | 1.0 | これだけ変わったらすぐ送る（°C） |
| `param_battery` / `param_temp` / `param_charging` | `FrameBattery` など | パラメーター名 |
| `chatbox` / `chatbox_interval_s` / `chatbox_format` | false / 10 / `Frame 🔋{battery}%{charging} 🌡{temp:.0f}°C` | チャットボックス |

設定を変えたら `systemctl --user restart frame-vitals-osc`。

## コマンドラインオプション

`--config FILE` / `--target host:port` / `--once` / `--dry-run` / `--duration 秒` / `--chatbox` / `-v` / `--version`

## テスト

```sh
python3 tests/test_frame_vitals_osc.py                               # OSC の組み立てと localhost での送受信
python3 tests/test_frame_vitals_osc.py --listen 19000 --seconds 60   # 受け取った中身を表示（本体は --target 127.0.0.1:19000）
```
