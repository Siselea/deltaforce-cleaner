"""Headless CLI: python main.py --cli [--dry-run]

Useful for scripting / CI, and lets the same engine be tested without a display.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

import engine  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="三角洲行动 卸载工具（命令行）")
    ap.add_argument("--cli", action="store_true", help="命令行模式")
    ap.add_argument("--dry-run", action="store_true", help="只扫描不删除")
    ap.add_argument("--no-game", action="store_true", help="跳过游戏本体")
    ap.add_argument("--no-ace", action="store_true", help="跳过 ACE 反作弊")
    ap.add_argument("--no-wegame", action="store_true", help="跳过 WeGame")
    ap.add_argument("--yes", action="store_true", help="跳过确认")
    args = ap.parse_args(argv)

    cfg = {
        "include": {
            "game": not args.no_game,
            "ace": not args.no_ace,
            "wegame": not args.no_wegame,
        }
    }
    print(f"管理员权限: {'是' if engine.is_admin() else '否'}")
    res = engine.scan(cfg)
    if not res.items:
        for n in res.notes:
            print("·", n)
        return 0

    print(f"\n发现 {len(res.items)} 项，预计释放 {engine.human_size(res.total_bytes)}：")
    for item in res.items:
        size = engine.human_size(item.size) if item.size else "-"
        print(f"  [{item.kind:<8}] {item.label}  ({size})")

    for n in res.notes:
        print("·", n)

    if args.dry_run:
        print("\n(dry-run，未做修改)")
        return 0
    if not args.yes:
        if not engine.is_admin():
            print("\n警告：非管理员运行，ACE 相关操作可能失败。")
        if input("\n确认永久删除以上全部内容？输入 yes 继续：").strip().lower() != "yes":
            print("已取消。")
            return 1

    engine.execute(res.items, lambda m: print(" ", m))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
