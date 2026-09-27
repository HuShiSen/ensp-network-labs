#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 TCP 控制台向 eNSP 设备批量下发配置（带逐行回显检查）

为什么需要它：
    手工把配置粘进 eNSP 控制台，很容易出现"命令发到了错误视图、静默报错被忽略"
    ——看起来跑完了，其实没生效。本脚本逐行下发、收集回显、把报错行标出来，
    再配合 verify_output.py 做关键字校验，能把这类问题在当场暴露。

用法：
    # 1) 先干跑，看看会下发哪些命令（跳过注释与空行）
    python push_config.py --file configs/01_vlan_trunk/core-switch.txt --dry-run

    # 2) 真下发（端口是 eNSP 里该设备控制台的本地监听端口）
    python push_config.py --port 2000 --file configs/01_vlan_trunk/core-switch.txt

    # 3) 需要登录时提供账号（实验环境默认口令，生产勿用）
    python push_config.py --port 2000 --file xxx.txt --user admin --password Admin@12345

    # 4) 下发完成后保存（send 'save' + 'Y' + 空行，一次写入，避免被吞回车）
    python push_config.py --port 2000 --file xxx.txt --save

约定：
    · 文件里以 # 开头的行视为注释，不下发（本仓库配置文件的说明块都用 # 包裹）
    · 除了 # 注释，也支持 ; 注释
    · 退出码：0 = 无错误行；1 = 有疑似报错行（需要人工看回显）
"""
from __future__ import annotations

import argparse
import re
import socket
import sys
import time

ERROR_PATTERNS = [
    r"Error[:\s]", r"Unrecognized command", r"Wrong parameter", r"Incomplete command",
    r"Too many parameters", r"Ambiguous command", r"^%\s", r"命令不存在",
]
ERROR_RE = re.compile("|".join(ERROR_PATTERNS), re.I)

PROMPT_RE = re.compile(r"[<\[]([^>\]]+)[>\]]\s*$")


def load_commands(path: str) -> list[str]:
    cmds = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n").rstrip("\r")
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith(";"):
                continue
            cmds.append(stripped)
    return cmds


def read_until_idle(sock: socket.socket, idle: float = 0.6, max_wait: float = 20.0) -> str:
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


def send_line(sock: socket.socket, line: str, delay: float) -> str:
    sock.sendall((line + "\r").encode())
    time.sleep(delay)
    return read_until_idle(sock, idle=max(delay, 0.4))


def login_if_needed(sock: socket.socket, user: str | None, password: str | None, delay: float) -> str:
    banner = read_until_idle(sock, idle=1.0, max_wait=8)
    if "Username" in banner or "login" in banner.lower():
        if not user:
            print("！设备要求登录，请用 --user/--password 提供账号", file=sys.stderr)
            sys.exit(2)
        banner += send_line(sock, user, delay)
        banner += send_line(sock, password, delay)
    return banner


def main() -> int:
    ap = argparse.ArgumentParser(description="向 eNSP 设备控制台批量下发配置")
    ap.add_argument("--host", default="127.0.0.1", help="eNSP 运行主机（默认本机）")
    ap.add_argument("--port", type=int, required=True, help="设备控制台监听端口（eNSP 里可查）")
    ap.add_argument("--file", required=True, help="配置文件路径")
    ap.add_argument("--delay", type=float, default=0.35, help="每条命令后的等待秒数（默认 0.35）")
    ap.add_argument("--user"), ap.add_argument("--password")
    ap.add_argument("--save", action="store_true", help="下发完执行 save（一次写入 save/Y/空行）")
    ap.add_argument("--dry-run", action="store_true", help="只打印将下发的命令，不连接设备")
    args = ap.parse_args()

    cmds = load_commands(args.file)
    if not cmds:
        print("！文件里没有可下发的命令（是否全是注释？）", file=sys.stderr)
        return 2

    print(f"== 待下发 {len(cmds)} 条命令（来源 {args.file}）==")
    for c in cmds:
        print("   >", c)
    if args.dry_run:
        print("（dry-run：未连接设备）")
        return 0

    print(f"\n== 连接 {args.host}:{args.port} ==")
    with socket.create_connection((args.host, args.port), timeout=10) as sock:
        login_if_needed(sock, args.user, args.password, args.delay)

        errors: list[tuple[str, str]] = []
        for i, cmd in enumerate(cmds, 1):
            out = send_line(sock, cmd, args.delay)
            bad = [l.strip() for l in out.splitlines() if ERROR_RE.search(l)]
            status = "OK " if not bad else "ERR"
            print(f"   [{i:3d}/{len(cmds)}] {status} {cmd}")
            if bad:
                for b in bad[:3]:
                    print(f"           ↳ {b}")
                errors.append((cmd, " | ".join(bad[:3])))

        if args.save:
            print("   [save] 一次写入 save / Y / 空行")
            sock.sendall(b"save\r")
            time.sleep(1.2)
            sock.sendall(b"Y\r")
            time.sleep(1.0)
            sock.sendall(b"\r")
            print(read_until_idle(sock, idle=1.5, max_wait=30))

    print("\n== 结果 ==")
    if errors:
        print(f"有 {len(errors)} 条命令出现疑似报错，请核对回显（多半是视图不对或参数写错）：")
        for cmd, err in errors:
            print(f"   ! {cmd}\n     {err}")
        print("\n提示：先确认当前视图（display current-configuration | include sysname 之类），"
              "再用 verify_output.py 逐项校验。")
        return 1

    print("全部命令无报错回显。⚠️ 这不等于生效：请务必执行")
    print("   python verify_output.py --port %d --check \"display current-configuration | include sysname\"" % args.port)
    print("   并按 docs/VERIFY_CHECKLIST.md 逐项验收，最后确认已 save。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
