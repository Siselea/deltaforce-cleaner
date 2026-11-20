"""Delta Force Cleaner - core engine.

Everything that touches the machine lives here. The GUI only calls scan() and
execute(); both are pure data in / data out so they can be unit-tested.
"""
from __future__ import annotations

import ctypes
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable

# --------------------------------------------------------------------------
# Constants: the ACE (AntiCheatExpert) surface, learned from a real machine.
# --------------------------------------------------------------------------

ACE_SERVICES = [
    "AntiCheatExpert Service",
    "AntiCheatExpert Protection",
    "ACE-ADVT",
    "ACE-BOOT",
    "ACE-CORE102706",
    "ACE-CORE202706",
    "ACE-CORE302706",
    "ACE-CORE302706",
    "ACE-GAME",
    "ACE-SSC-DRV64",
]

# Never touch these: they are Windows in-box storage drivers that merely match "ace".
PROTECTED_SERVICE_NAMES = {"filetrace", "spaceparser", "spaceport", "spacedump", "pacer"}

# Game / launcher directories found relative to a drive root.
GAME_DIR_NAMES = ["Delta Force", "DeltaForce", "rail_user_data"]

# WeGame-only subdirectories under %APPDATA%\Tencent. xwechat (WeChat) and
# qimei (shared mini-program data) are deliberately absent.
WEGAME_DIRS = ["WeGame", "WGLogin", "TenioDL", "DeskUpdate", "CTLogin", "TXSSO", "Logs", "libsdk"]

ACE_UNINSTALL_SUBKEYS = [r"AntiCheatExpert"]

WEGAME_REGKEY = r"SOFTWARE\WOW6432Node\Tencent\WeGame"


@dataclass
class Item:
    """One discrete thing that can be removed."""

    kind: str          # service | dir | regkey | regvalue | file
    label: str         # human readable, shown in the UI
    target: str        # path or registry path
    size: int = 0
    delete_children_only: bool = False


@dataclass
class ScanResult:
    items: list[Item] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(i.size for i in self.items)


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:,.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024.0
    return f"{n:,.1f} TB"


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def drive_roots() -> list[str]:
    roots = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        root = f"{letter}:\\"
        if os.path.exists(root):
            roots.append(root)
    return roots


def dir_size(path: str, budget: int = 300_000, seconds: float = 1.5) -> int:
    """Sum file sizes, bailing out early for enormous trees.

    The game folder can hold 100k+ files; measuring it must never stall the UI,
    so both a file-count and a wall-clock budget apply.
    """
    total = 0
    seen = 0
    deadline = time.time() + seconds
    for base, _dirs, files in os.walk(path, onerror=lambda e: None):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(base, name))
            except OSError:
                pass
            seen += 1
            if seen > budget or (seen % 512 == 0 and time.time() > deadline):
                return total
    return total


def _run(args: list[str], timeout: int = 20) -> str:
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return (proc.stdout or b"").decode("mbcs", "replace")
    except Exception:
        return ""


# --------------------------------------------------------------------------
# Registry helpers
# --------------------------------------------------------------------------

def reg_enum_services() -> list[str]:
    out = _run(["reg", "query", r"HKLM\SYSTEM\CurrentControlSet\Services"])
    names = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("HKEY_LOCAL_MACHINE"):
            names.append(line.rsplit("\\", 1)[-1])
    return names


def reg_key_exists(path: str) -> bool:
    return bool(_run(["reg", "query", path]).strip()) and "ERROR" not in _run(["reg", "query", path]).upper()


def reg_read_values(path: str) -> dict[str, str]:
    out = _run(["reg", "query", path])
    values: dict[str, str] = {}
    for line in out.splitlines():
        m = re.match(r"\s{2,}(\S+)\s{2,}(\S+)\s{2,}(.*)$", line)
        if m:
            values[m.group(1)] = m.group(3).strip()
    return values


def reg_enum_subkeys(path: str) -> list[str]:
    out = _run(["reg", "query", path])
    subs = []
    for line in out.splitlines():
        line = line.strip()
        if line.upper().startswith("HKEY_") and line.upper() != path.upper():
            subs.append(line)
    return subs


# --------------------------------------------------------------------------
# Scanning
# --------------------------------------------------------------------------

def _add(res: ScanResult, label: str, fn, progress=None):
    """Run one probe; a single broken probe must never abort the whole scan."""
    try:
        fn(res)
        if progress:
            progress(label)
    except Exception as exc:  # noqa: BLE001
        res.notes.append(f"{label} 检查失败：{exc}")


def scan(cfg: dict | None = None, progress: Callable[[str], None] | None = None) -> ScanResult:
    cfg = cfg or {}
    res = ScanResult()
    want = cfg.get("include", {})
    do_game = want.get("game", True)
    do_ace = want.get("ace", True)
    do_wegame = want.get("wegame", True)
    nosize = bool(cfg.get("no_size", False))

    def size_of(path: str) -> int:
        return 0 if nosize else dir_size(path)

    env = os.environ
    appdata = env.get("APPDATA", "")
    localappdata = env.get("LOCALAPPDATA", "")
    programdata = env.get("ProgramData", r"C:\ProgramData")

    # ---- 1. ACE services -------------------------------------------------
    if do_ace:
        live = {n.lower() for n in reg_enum_services()}
        for name in dict.fromkeys(ACE_SERVICES):
            if name.lower() in PROTECTED_SERVICE_NAMES:
                continue
            state = _run(["sc", "query", name])
            if "SERVICE_NAME" in state or name.lower() in live:
                running = "RUNNING" in state.upper()
                res.items.append(
                    Item("service", f"{name}{'  (运行中)' if running else ''}", name)
                )

        for key in ACE_UNINSTALL_SUBKEYS:
            for hive in (
                r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            ):
                path = hive + "\\" + key
                if reg_read_values(path):
                    res.items.append(Item("regkey", f"卸载项 {key}", path))

        for ace_dir in (
            os.path.join(r"C:\Program Files", "AntiCheatExpert"),
            os.path.join(r"C:\Program Files (x86)", "AntiCheatExpert"),
            os.path.join(programdata, "AntiCheatExpert"),
        ):
            if os.path.isdir(ace_dir):
                res.items.append(Item("dir", f"ACE 程序目录 {ace_dir}", ace_dir, size_of(ace_dir)))

    # ---- 2. Game directories --------------------------------------------
    if do_game:
        for root in drive_roots():
            for name in GAME_DIR_NAMES:
                p = os.path.join(root, name)
                if os.path.isdir(p):
                    res.items.append(Item("dir", f"游戏目录 {p}", p, size_of(p)))

        for rel in (
            os.path.join(appdata, "deltaforceminiloader"),
            os.path.join(appdata, "delta_force_launcher"),
            os.path.join(localappdata, "deltaforceminiloader"),
            os.path.join(localappdata, "delta_force_launcher"),
        ):
            if os.path.isdir(rel):
                res.items.append(Item("dir", f"启动器数据 {rel}", rel, size_of(rel)))

        # Uninstall entries naming the game.
        for hive in (
            r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        ):
            for sub in reg_enum_subkeys(hive):
                vals = reg_read_values(sub)
                blob = json.dumps(vals, ensure_ascii=False).lower()
                leaf = sub.rsplit("\\", 1)[-1].lower()
                if "delta force" in blob or "三角洲" in blob or "delta_force" in leaf:
                    if "anticheatexpert" in leaf:
                        continue
                    res.items.append(Item("regkey", f"游戏卸载项 {sub.rsplit('\\', 1)[-1]}", sub))

        # Start-menu folders / desktop shortcuts.
        for menu in (
            os.path.join(programdata, r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs"),
        ):
            if os.path.isdir(menu):
                for name in os.listdir(menu):
                    low = name.lower()
                    if "delta force" in low or "三角洲" in name:
                        p = os.path.join(menu, name)
                        res.items.append(Item("dir", f"开始菜单 {name}", p, size_of(p)))

    # ---- 3. WeGame leftovers --------------------------------------------
    if do_wegame:
        wgkey = "HKLM\\" + WEGAME_REGKEY
        if reg_read_values(wgkey) or reg_enum_subkeys(wgkey) or reg_key_exists(wgkey):
            res.items.append(Item("regkey", "WeGame 注册表", wgkey))

        for sub in WEGAME_DIRS:
            p = os.path.join(appdata, "Tencent", sub)
            if os.path.isdir(p):
                # "Logs" only belongs to us when it holds Delta Force traces.
                if sub == "Logs" and not _has_delta_trace(p):
                    continue
                res.items.append(Item("dir", f"WeGame 数据 {p}", p, size_of(p)))

    if not res.items:
        res.notes.append("未发现《三角洲行动》、ACE 反作弊或 WeGame 残留。系统已经是干净状态。")
    if not is_admin():
        res.notes.append("当前未以管理员身份运行：ACE 服务/驱动删除与部分系统目录可能需要提权。")
    return res


def _has_delta_trace(folder: str) -> bool:
    try:
        return any("delta" in n.lower() for n in os.listdir(folder))
    except OSError:
        return False


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------

def _stop_and_delete_service(name: str, log: Callable[[str], None]) -> bool:
    state = _run(["sc", "stop", name])
    log(f"    stop  → {state.strip().splitlines()[-1] if state.strip() else 'ok'}")
    time.sleep(0.4)
    out = _run(["sc", "delete", name])
    ok = "SUCCESS" in out.upper()
    log(f"    delete→ {'OK' if ok else 'FAIL: ' + out.strip()[:120]}")
    return ok


def _delete_regkey(path: str, log: Callable[[str], None]) -> bool:
    out = _run(["reg", "delete", path, "/f"])
    ok = "成功" in out or "SUCCESS" in out.upper() or not out.strip()
    log(f"    regdel→ {'OK' if ok else 'FAIL: ' + out.strip()[:120]}")
    return ok


def _delete_dir(path: str, log: Callable[[str], None]) -> bool:
    """Delete a tree; fall back to shell32 for long paths / odd ACLs."""
    try:
        import shutil

        shutil.rmtree(path)
        return not os.path.exists(path)
    except Exception as exc:
        log(f"    rmtree 失败（{exc}），尝试 SHFileOperation…")
        try:
            res = ctypes.windll.shell32.SHFileOperationW
            # FOF_SILENT | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_ALLOWUNDO=0
            class SHFILEOPSTRUCTW(ctypes.Structure):
                _fields_ = [
                    ("hwnd", ctypes.c_void_p),
                    ("wFunc", ctypes.c_uint),
                    ("pFrom", ctypes.c_wchar_p),
                    ("pTo", ctypes.c_wchar_p),
                    ("fFlags", ctypes.c_ushort),
                    ("fAnyOperationsAborted", ctypes.c_int),
                    ("hNameMappings", ctypes.c_void_p),
                    ("lpszProgressTitle", ctypes.c_wchar_p),
                ]

            op = SHFILEOPSTRUCTW(
                None, 3, path + "\0\0", None, 0x0004 | 0x0010 | 0x0400, 0, None, None
            )
            rc = res(ctypes.byref(op))
            return rc == 0 and not os.path.exists(path)
        except Exception as exc2:
            log(f"    SHFileOperation 也失败：{exc2}")
            return False


def execute(items: Iterable[Item], log: Callable[[str], None], dry_run: bool = False) -> dict:
    items = list(items)
    done, failed = 0, 0
    freed = 0
    log(f"开始{'（试运行，不做任何修改）' if dry_run else ''}，共 {len(items)} 项")

    for idx, item in enumerate(items, 1):
        log(f"[{idx}/{len(items)}] {item.label}")
        if dry_run:
            log("    跳过（dry-run）")
            done += 1
            freed += item.size
            continue

        if item.kind == "service":
            ok = _stop_and_delete_service(item.target, log)
        elif item.kind == "regkey":
            ok = _delete_regkey(item.target, log)
        elif item.kind == "dir":
            ok = _delete_dir(item.target, log)
        else:
            log(f"    未知类型 {item.kind}")
            ok = False

        if ok:
            done += 1
            freed += item.size
        else:
            failed += 1

    log(f"完成：成功 {done} 项，失败 {failed} 项，释放约 {human_size(freed)}")
    if not dry_run and any(i.kind == "service" for i in items):
        log("提示：ACE 是内核级驱动，建议重启一次让驱动模块彻底从内存卸载。")
    return {"ok": done, "failed": failed, "freed": freed}


def relaunch_as_admin(argv: list[str]) -> bool:
    """Re-launch this process elevated. Returns True if the shell accepted it."""
    try:
        params = " ".join(sys.argv[1:])
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        return rc > 32
    except Exception:
        return False
