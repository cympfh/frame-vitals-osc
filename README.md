# frame-vitals-osc

Steam Frame の **電池残量・充電中かどうか・本体の温度** を VRChat のアバターに届けます。
アバターに電池メーターを付けたり、本体が熱くなったらアバターが汗をかくようにしたりできます。

```
FrameBattery  = 0.73   ← 電池 73%
FrameTemp     = 0.40   ← 温度（30 °C で 0、95 °C で 1）
FrameCharging = true   ← 充電中
```

## インストール

Frame の Konsole に貼り付けて Enter:

```sh
curl -fsSL https://raw.githubusercontent.com/cympfh/frame-vitals-osc/main/install.sh | bash
```

## オン・オフ

```sh
systemctl --user enable --now frame-vitals-osc    # オン（次からは SteamVR と一緒に起動）
systemctl --user disable --now frame-vitals-osc   # オフ
```

## VRChat の準備

- アバターの Expression Parameters に `FrameBattery`（Float）、`FrameTemp`（Float）、`FrameCharging`（Bool）を追加して、アニメーターで使う
- VRChat のアクションメニュー → オプション → OSC → 有効
- パラメーターを足したアバターが反応しないときは、同じメニューの「Reset Config」を押す
- 送り先の PC は [frameeyeosc](https://github.com/sasaken1102r/frameeyeosc) と同じです（入っていなければ設定ファイルで指定）

## アンインストール

```sh
curl -fsSL https://raw.githubusercontent.com/cympfh/frame-vitals-osc/main/install.sh | bash -s -- --uninstall
```

外したファイルは消さずに `~/.local/share/frame-vitals-osc-uninstalled/` へ移します。設定ファイルは残ります。

<details>
<summary>くわしい情報（設定・開発者向け）</summary>

- 設定ファイル: `~/.config/frame-vitals-osc/config.json`（初回にサンプルからコピー）。項目は [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- チャットボックス表示（`Frame 🔋73% ⚡ 🌡48°C`）もできます。最初はオフ、オンでも 10 秒に 1 回まで
- ログ: `journalctl --user -u frame-vitals-osc -f`
- Python 3 の標準ライブラリだけで動き、sudo は使いません

</details>
