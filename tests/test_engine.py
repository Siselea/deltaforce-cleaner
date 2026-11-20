"""Smoke tests: run with  python -m pytest -q  or  python tests/test_engine.py"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

import engine  # noqa: E402


def test_human_size():
    assert engine.human_size(0) == "0 B"
    assert engine.human_size(1024) == "1.0 KB"
    assert engine.human_size(1024 ** 3).startswith("1.0 GB")


def test_protected_services_never_scanned():
    names = {n.lower() for n in engine.ACE_SERVICES}
    assert not (names & engine.PROTECTED_SERVICE_NAMES), "系统存储驱动不能被当成 ACE"


def test_wegame_list_excludes_wechat_data():
    lowered = {d.lower() for d in engine.WEGAME_DIRS}
    assert "xwechat" not in lowered
    assert "qimei" not in lowered


def test_drive_roots_are_absolute():
    for root in engine.drive_roots():
        assert len(root) == 3 and root[1] == ":" and root[2] == "\\"


def test_scan_returns_scanresult():
    res = engine.scan({"include": {"game": True, "ace": True, "wegame": True}})
    assert isinstance(res, engine.ScanResult)
    assert isinstance(res.total_bytes, int)


def test_dir_size_of_missing_path_is_zero():
    assert engine.dir_size("Z:\\does-not-exist\\nope") == 0


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("PASS", name)
