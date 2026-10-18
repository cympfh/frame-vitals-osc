#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""frame-vitals-osc: Steam Frame のバッテリー・充電状態・SoC 温度を VRChat に OSC で送る。

依存なし（Python 3 標準ライブラリだけ）。ユーザー権限で動き、読むのは /sys の値だけ。
"""
import argparse
import json
import os
import re
import shlex
import signal
import socket
import struct
import time

VERSION = "0.1.0"
HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_CONFIG = {
    "host": "auto",              # "auto" = frameeyeosc と同じ送り先。または "192.168.1.10" のような IP
    "port": 9000,                # host を指定したときのポート（VRChat の OSC 受信は 9000）
    "interval_s": 2.0,           # 値を読む間隔（秒）
    "keepalive_s": 10.0,         # 値が変わらなくても、この間隔で送り直す（秒）
    "temp_min_c": 30.0,          # FrameTemp = 0.0 になる温度
    "temp_max_c": 95.0,          # FrameTemp = 1.0 になる温度
    "param_prefix": "/avatar/parameters/",
    "param_battery": "FrameBattery",
    "param_temp": "FrameTemp",
    "param_charging": "FrameCharging",
    "chatbox": False,            # チャットボックスへの表示（既定オフ）
    "chatbox_interval_s": 10.0,  # 最短 10 秒（それより短い値は 10 秒に切り上げ）
    "chatbox_format": "Frame 🔋{battery}%{charging} 🌡{temp:.0f}°C",
    "log_every_s": 60.0,         # この間隔で状態をログに出す
}
MIN_CHATBOX_INTERVAL_S = 10.0


def log(*args):
    print(time.strftime("%H:%M:%S"), *args, flush=True)


# ---------------------------------------------------------------- OSC 1.0 (送信だけ)
def _pad(b):
    return b + b"\0" * (4 - len(b) % 4)


def osc_message(address, *args):
    """OSC メッセージを組み立てる。float / int / str / bool に対応。"""
    tags, data = ",", b""
    for v in args:
        if v is True:
            tags += "T"
        elif v is False:
            tags += "F"
        elif isinstance(v, float):
            tags += "f"
            data += struct.pack(">f", v)
        elif isinstance(v, int):
            tags += "i"
            data += struct.pack(">i", v)
        elif isinstance(v, str):
            tags += "s"
            data += _pad(v.encode("utf-8"))
        else:
            raise TypeError(f"OSC にできない型: {type(v)}")
    return _pad(address.encode()) + _pad(tags.encode()) + data


# ---------------------------------------------------------------- センサー
def read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def find_battery(base="/sys/class/power_supply"):
    if not os.path.isdir(base):
        return None
    for n in sorted(os.listdir(base)):
        if read(f"{base}/{n}/type") == "Battery" and read(f"{base}/{n}/capacity") is not None:
            return f"{base}/{n}"
    return None


def find_soc_zones(base="/sys/class/thermal"):
    """CPU / GPU の温度ゾーン（Frame では cpu*-thermal, cpuss*-thermal, gpuss-*-thermal）。"""
    zones = []
    if not os.path.isdir(base):
        return zones
    for n in sorted(os.listdir(base)):
        t = read(f"{base}/{n}/type") or ""
        if re.match(r"^(cpu|cpuss|gpuss)", t):
            zones.append(f"{base}/{n}/temp")
    return zones


def soc_temp(zones):
    """いちばん熱いゾーンの温度（°C）。"""
    vals = []
    for z in zones:
        v = read(z)
        if v and v.lstrip("-").isdigit():
            vals.append(int(v) / 1000.0)
    return max(vals) if vals else None


# ---------------------------------------------------------------- 設定と送り先
def load_config(path):
    cfg = dict(DEFAULT_CONFIG)
    if path and os.path.exists(path):
        with open(path) as f:
            user = json.load(f)
        for k in user:
            if k not in DEFAULT_CONFIG and not k.startswith("_"):
                log(f"警告: 知らない設定キー {k!r} は無視します")
        cfg.update({k: v for k, v in user.items() if k in DEFAULT_CONFIG})
    return cfg


def parse_target(value):
    host, port = value.rsplit(":", 1)
    return host, int(port)


def frameeyeosc_target(home=None):
    """frameeyeosc の送り先 (host, port, 理由) を探す。見つからなければ None。"""
    home = home or os.path.expanduser("~")
    env = read(f"{home}/.config/frameeyeosc/env") or ""
    for line in env.splitlines():
        m = re.match(r"\s*FRAMEEYEOSC_ARGS=(.*)", line)
        if not m:
            continue
        try:
            args = shlex.split(" ".join(shlex.split(m.group(1))))
        except ValueError:
            continue
        for i, a in enumerate(args):
            val = None
            if a == "--target" and i + 1 < len(args):
                val = args[i + 1]
            elif a.startswith("--target="):
                val = a.split("=", 1)[1]
            if val and ":" in val and val.rsplit(":", 1)[1].isdigit():
                return (*parse_target(val), "frameeyeosc の env (--target)")
    try:
        with open(f"{home}/.config/frameeyeosc/config.json") as f:
            j = json.load(f)
        h = j.get("host")
        if h and h != "auto":
            return h, int(j.get("port") or 9000), "frameeyeosc の config.json"
    except (OSError, ValueError):
        pass
    return None


def resolve_target(cfg, override=None):
    if override:
        return (*parse_target(override), "--target")
    if cfg["host"] != "auto":
        return cfg["host"], int(cfg["port"]), "config.json"
    t = frameeyeosc_target()
    if t:
        return t
    return "127.0.0.1", int(cfg["port"]), "既定 (127.0.0.1)"


# ---------------------------------------------------------------- 本体
def main(argv=None):
    ap = argparse.ArgumentParser(description="Steam Frame のバイタルを VRChat に OSC で送る")
    ap.add_argument("--config", default=os.path.join(HERE, "config.json"), help="設定ファイル（既定: このフォルダの config.json）")
    ap.add_argument("--target", help="送り先 host:port（設定より優先）")
    ap.add_argument("--once", action="store_true", help="1 回だけ読んで送って終わる")
    ap.add_argument("--dry-run", action="store_true", help="送らずに表示だけ")
    ap.add_argument("--duration", type=float, default=0, help="この秒数で終わる（テスト用）")
    ap.add_argument("--chatbox", action="store_true", help="チャットボックス送信を有効にする（設定より優先）")
    ap.add_argument("-v", "--verbose", action="store_true", help="送るたびに表示")
    ap.add_argument("--version", action="version", version=f"frame-vitals-osc {VERSION}")
    a = ap.parse_args(argv)

    cfg = load_config(a.config)
    if a.chatbox:
        cfg["chatbox"] = True
    host, port, why = resolve_target(cfg, a.target)
    chat_iv = max(MIN_CHATBOX_INTERVAL_S, float(cfg["chatbox_interval_s"]))
    bat = find_battery()
    zones = find_soc_zones()
    log(f"frame-vitals-osc {VERSION}: 送り先 {host}:{port}（{why}） バッテリー={bat} "
        f"SoC温度ゾーン={len(zones)}個 チャットボックス={'オン' if cfg['chatbox'] else 'オフ'}"
        f"{' (dry-run)' if a.dry_run else ''}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    stop = {"v": False}

    def on_signal(*_):
        stop["v"] = True

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    pre = cfg["param_prefix"]
    last_sent, last_vals, last_chat, last_log = 0.0, None, -1e9, time.monotonic()
    counters = {"sent": 0, "errors": 0}
    t0 = time.monotonic()

    def send(addr, *args):
        if a.verbose or a.dry_run:
            log("->", addr, *args)
        if a.dry_run:
            return
        try:
            sock.sendto(osc_message(addr, *args), (host, port))
            counters["sent"] += 1
        except OSError as e:
            counters["errors"] += 1
            if counters["errors"] <= 3 or counters["errors"] % 100 == 0:
                log(f"送信エラー（{counters['errors']} 回目）: {e}")

    while not stop["v"]:
        now = time.monotonic()
        cap = read(f"{bat}/capacity") if bat else None
        status = read(f"{bat}/status") if bat else None
        battery = max(0.0, min(1.0, int(cap) / 100.0)) if cap and cap.isdigit() else None
        charging = status in ("Charging", "Full")
        temp = soc_temp(zones)
        tnorm = None
        if temp is not None:
            span = max(1e-6, cfg["temp_max_c"] - cfg["temp_min_c"])
            tnorm = max(0.0, min(1.0, (temp - cfg["temp_min_c"]) / span))

        vals = (battery, charging, None if tnorm is None else round(tnorm, 2))
        if vals != last_vals or now - last_sent >= cfg["keepalive_s"]:
            if battery is not None:
                send(pre + cfg["param_battery"], float(battery))
            if tnorm is not None:
                send(pre + cfg["param_temp"], float(round(tnorm, 3)))
            send(pre + cfg["param_charging"], bool(charging))
            last_sent, last_vals = now, vals

        if cfg["chatbox"] and battery is not None and now - last_chat >= chat_iv:
            text = cfg["chatbox_format"].format(
                battery=round(battery * 100), temp=temp or 0.0, charging=" ⚡" if charging else "")
            send("/chatbox/input", text[:144], True, False)  # すぐ表示する・通知音なし
            last_chat = now

        if now - last_log >= cfg["log_every_s"]:
            log(f"状態: バッテリー {cap}% {status} / SoC {temp}°C (FrameTemp {tnorm and round(tnorm, 3)}) "
                f"/ 送信 {counters['sent']} パケット / エラー {counters['errors']}")
            last_log = now

        if a.once or (a.duration and now - t0 >= a.duration):
            break
        slept = 0.0
        while slept < cfg["interval_s"] and not stop["v"]:
            time.sleep(0.2)
            slept += 0.2

    log(f"終了: 送信 {counters['sent']} パケット / エラー {counters['errors']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
