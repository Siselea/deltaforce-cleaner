# How detection works

This document records *why* each rule exists, based on a real cleanup performed on
Windows 11 (26300) with Delta Force installed via WeGame.

## 1. Services and drivers

ACE registers up to a dozen kernel/service entries. Names are versioned
(`ACE-CORE102706` — the suffix tracks the ACE build), so the scanner matches on the
`ACE-*` family plus the two long-form names:

```
AntiCheatExpert Service, AntiCheatExpert Protection,
ACE-ADVT, ACE-BOOT, ACE-CORE*, ACE-GAME, ACE-SSC-DRV64
```

**Trap:** `sc query` also returns `filetrace`, `spaceparser`, `spaceport` on some
systems because `sc` does substring matching. Those are Windows in-box storage
drivers. They are listed in `PROTECTED_SERVICE_NAMES` and filtered out before any
other logic runs. Deleting `spaceport` takes the filesystem offline.

## 2. Files

| Path | Note |
|---|---|
| `C:\Program Files\AntiCheatExpert` | Contains `ACE-BASE.sys`, `ACE-BOOT.sys`, `ACE-CORE*.sys`, `ACE-Service64.exe`, `ACE-Tray.exe`, `Uninstaller.exe` |
| `C:\ProgramData\AntiCheatExpert` | `ACE-Tray.dat`, `ace-drc.dat`, `sldh.dat` |
| `<drive>:\Delta Force` | Game root; can exceed 19 GB |
| `<drive>:\rail_user_data` | Empty engine cache; usually missed by manual cleanup |

The official `Uninstaller.exe` is respected when present — it removes its own files
and registry keys more reliably than deleting them by hand.

## 3. Registry

```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\AntiCheatExpert
HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\三角洲行动
HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\delta_force_launcher
HKLM\SOFTWARE\WOW6432Node\Tencent\WeGame          <- WeGame remnant
```

`UninstallString` values frequently point at a drive letter (`U:\`) that no longer
exists. That is the signal that a manual removal is required.

## 4. WeGame data

WeGame stores per-title caches beside its own login state under
`%APPDATA%\Tencent`. The tool removes only the WeGame-specific folder names.

`Logs` is special-cased: it belongs to WeGame, but is only deleted when it actually
contains Delta Force traces (`delta_force_launcher.tlg*`). Otherwise WeGame may still
be installed for other titles and those logs are not ours to take.

## 5. What is deliberately excluded

`%APPDATA%\Tencent\xwechat` (WeChat), `qimei` (shared mini-program database), and all
QQ folders share the `Tencent` parent. Deleting the parent to "clean up" would
destroy the user's messenger installation. The tool never recurses into `Tencent`
as a whole.

## 6. Verification

After a run the tool reports item counts; a clean re-scan should return zero items
(plus the admin note if unelevated). A reboot is recommended so that the kernel
module, already unlinked from disk, is also released from memory.