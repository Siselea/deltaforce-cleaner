# Delta Force Cleaner

[中文说明](README.zh-CN.md) · [License: MIT](LICENSE) · [Contributing](CONTRIBUTING.md)

A clean uninstaller for **Delta Force** (三角洲行动) on Windows. It removes the game
itself **and** every trace of Tencent's **ACE (AntiCheatExpert)** anti-cheat drivers,
services, and leftover files.

[中文说明](README.zh-CN.md) · [License: MIT](LICENSE)

## Why this exists

Uninstalling Delta Force normally leaves behind a kernel-level anti-cheat driver that
stays on the system indefinitely. ACE registers 12+ services and drivers, writes to
`System32\drivers`, `Program Files`, `ProgramData`, and several registry hives. This
tool encodes the full cleanup, item by item, into something that can be reviewed,
tested, and re-run.

## What it removes

| Category | Contents |
|---|---|
| Game | `Delta Force` / `DeltaForce` / `rail_user_data` folders on every drive |
| ACE services | `AntiCheatExpert Service/Protection`, `ACE-ADVT`, `ACE-BOOT`, `ACE-CORE*`, `ACE-GAME`, `ACE-SSC-DRV64` |
| ACE files | `C:\Program Files\AntiCheatExpert`, `C:\ProgramData\AntiCheatExpert` |
| Registry | ACE and game uninstall entries, `Tencent\WeGame` |
| Launcher | `deltaforceminiloader`, `delta_force_launcher`, Start Menu shortcuts |
| WeGame | WeGame-only folders under `%APPDATA%\Tencent` |

## What it never touches

- `filetrace.sys`, `spaceparser.sys`, `spaceport.sys` — Windows in-box **storage drivers** that merely match the string `ace`
- `%APPDATA%\Tencent\xwechat` (WeChat), `qimei` (shared mini-program data), QQ data

Removing those would damage the OS or your WeChat/QQ installation. Both rules are
enforced in code and covered by tests.

## Usage

Requires Python 3.9+ (uses only the standard library and Tk).

```
start.bat               # GUI (no console window)
python main.py          # same
```

Flow: **Scan → review the list (untick anything you want to keep) → Uninstall → read the log.**

### Command line

```bash
python main.py --cli --dry-run     # report only, changes nothing
python main.py --cli --yes         # scan and execute
python main.py --cli --no-wegame   # game + ACE only
```

## Administrator rights

ACE is a kernel-mode driver; deleting its services and system folders requires
elevation. When launched without it, the GUI shows a warning banner with a
**Relaunch as administrator** button.

**Reboot once afterwards** — the driver files are gone, but the loaded kernel module
only fully leaves memory after a restart.

## Safety design

- **Item-level consent** — every target is listed and individually toggleable; nothing is a black box.
- **Dry run** — simulate the whole plan without touching disk.
- **Per-item fault isolation** — one failure is logged and the rest continue.
- **Bounded probing** — directory sizing carries a 1.5 s budget so a 100k-file game folder never stalls the UI.
- **Long-path fallback** — `shutil.rmtree` falls back to `SHFileOperationW`.

## Layout

```
app/engine.py     scan, delete, elevate  (pure data in/out, unit-tested)
app/gui.py        Tk interface, worker threads keep the UI responsive
app/cli.py        command-line wrapper
main.py           entry point + single-instance mutex
tests/            smoke tests, run: python tests/test_engine.py
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Ideas for detection rules specific to other
ACE-protected Tencent titles are welcome, provided they include a test that proves
system drivers and messenger data stay untouched.

## License

MIT. Not affiliated with Tencent or the Delta Force developers. Use at your own risk.