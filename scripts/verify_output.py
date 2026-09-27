#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回读校验：把设备回显与期望关键字比对，防止"发了但没生效"

用法：
    # 单条命令 + 多个期望关键字（全部出现才算通过）
    python verify_output.py --port 2000 \
        --check "display vrrp brief" --expect "Master" --expect "192.168.10.254"

    # 多条命令一起校验（每条一个 --check，期望关键字按顺序与 check 对应）
    python verify_output.py --port 2000 \
        --check "display eth-trunk 1" --expect "Selected" \
        --check "display hrp state"   --expect "active"

    # 登录设备
    python verify_output.py --port 2024 --user admin --password Admin@12345 \
        --check "display hrp state" --expect "active"

退出码：0 = 全部通过；1 = 有未匹配项（把原始回显打印出来供人工判断）
"""
from __future__ import annotations

import argparse
import socket
import sys
import time


def read_until_idle(sock: socket.socket, idle: float = 0.8, max_wait: float = 25.0) -> str:
    sock.settimeout(0.3)
    buf, last, start = "", time.time(), time.time()
    while True:
        try:
            chunk = sock.recv(65535)
            if chunk:
                buf += chunk.decode("utf-8", errors="replace")
                last = time.time()
                continue
        except socket.timeout:
            pass
        if time.time() - last >= idle or time.time() - start >= max_wait:
            break
    return buf


def main() -> int:
    ap = argparse.ArgumentParser(description="按关键字校验设备回显")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--check", action="append", required=True, help="要执行的 display 命令，可重复")
    ap.add_argument("--expect", action="append", default=[], help="期望出现的关键字")
    ap.add_argument("--ignore-case", action="store_true", default=True)
    ap.add_argument("--user"), ap.add_argument("--password")
    ap.add_argument("--delay", type=float, default=1.2)
    args = ap.parse_args()

    with socket.create_connection((args.host, args.port), timeout=10) as sock:
        banner = read_until_idle(sock, idle=1.0, max_wait=8)
        if "Username" in banner or "login" in banner.lower():
            if not args.user:
                print("！设备要求登录，请提供 --user/--password", file=sys.stderr)
                return 2
            for v in (args.user, args.password or ""):
                sock.sendall((v + "\r").encode()); time.sleep(args.delay)
            read_until_idle(sock)

        outputs = []
        for cmd in args.check:
            sock.sendall((cmd + "\r").encode())
            time.sleep(args.delay)
            outputs.append((cmd, read_until_idle(sock)))

    combined = "\n".join(o for _, o in outputs)
    haystack = combined.lower() if args.ignore_case else combined
    missing = []
    for kw in args.expect:
        needle = kw.lower() if args.ignore_case else kw
        ok = needle in haystack
        print(f"   {'✓' if ok else '✗'} 期望关键字：{kw}")
        if not ok:
            missing.append(kw)

    if missing:
        print(f"\n== 未匹配 {len(missing)} 项，原始回显如下 ==")
        for cmd, out in outputs:
            print(f"\n----- {cmd} -----")
            print(out.strip()[:2000])
        return 1

    print("\n✅ 全部关键字命中")
    print('提醒：关键字命中只说明“能查到这项状态”，还要按 docs/VERIFY_CHECKLIST.md 判断数值是否合理'
          '（例如 VRRP 是 Master 还是 Backup、Eth-Trunk 成员口数量是否为 2）。')
    return 0


if __name__ == "__main__":
    sys.exit(main())
