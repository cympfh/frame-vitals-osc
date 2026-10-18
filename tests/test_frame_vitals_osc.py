#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""localhost に UDP で受けて、送られた OSC パケットを確かめるテスト。

  python3 tests/test_frame_vitals_osc.py            エンコードの単体テストと 6 秒の送受信テスト
  python3 tests/test_frame_vitals_osc.py --listen 19000 --seconds 60   受信して中身を表示するだけ
"""
import argparse
import os
import socket
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("fvo", os.path.join(ROOT, "frame-vitals-osc.py"))
fvo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fvo)


def _str(buf, i):
    end = buf.index(b"\0", i)
    s = buf[i:end].decode("utf-8")
    return s, (end + 4) & ~3


def decode(buf):
    addr, i = _str(buf, 0)
    tags, i = _str(buf, i)
    args = []
    for t in tags[1:]:
        if t == "f":
            args.append(round(struct.unpack(">f", buf[i:i + 4])[0], 3)); i += 4
        elif t == "i":
            args.append(struct.unpack(">i", buf[i:i + 4])[0]); i += 4
        elif t == "s":
            s, i = _str(buf, i); args.append(s)
        elif t == "T":
            args.append(True)
        elif t == "F":
            args.append(False)
    return addr, args


def unit_tests():
    for addr, args in [("/avatar/parameters/FrameBattery", (0.73,)),
                       ("/avatar/parameters/FrameCharging", (True,)),
                       ("/chatbox/input", ("Frame 🔋73% 🌡48°C", True, False))]:
        m = fvo.osc_message(addr, *args)
        assert len(m) % 4 == 0, "4 バイト境界でない"
        got = decode(m)
        want = (addr, [round(a, 3) if isinstance(a, float) else a for a in args])
        assert got == want, (got, want)
    print("単体テスト OK")


def listen(port, seconds):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", port))
    s.settimeout(0.5)
    got = []
    end = time.time() + seconds
    while time.time() < end:
        try:
            buf, _ = s.recvfrom(4096)
        except socket.timeout:
            continue
        msg = decode(buf)
        got.append(msg)
        print(time.strftime("%H:%M:%S"), "受信", *msg, flush=True)
    return got


def roundtrip():
    port = 19000 + os.getpid() % 1000
    p = subprocess.Popen([sys.executable, os.path.join(ROOT, "frame-vitals-osc.py"),
                          "--config", "/nonexistent", "--target", f"127.0.0.1:{port}",
                          "--duration", "4", "--chatbox"])
    got = listen(port, 6)
    p.wait()
    addrs = {a for a, _ in got}
    assert "/avatar/parameters/FrameCharging" in addrs, addrs
    print(f"送受信テスト OK（{len(got)} パケット、アドレス: {sorted(addrs)}）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", type=int)
    ap.add_argument("--seconds", type=float, default=60)
    a = ap.parse_args()
    if a.listen:
        got = listen(a.listen, a.seconds)
        print(f"合計 {len(got)} パケット受信")
    else:
        unit_tests()
        roundtrip()
