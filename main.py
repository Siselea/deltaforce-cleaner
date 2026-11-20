"""Entry point: python main.py  (or double-click 启动.bat)"""
import ctypes
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

MUTEX_NAME = "Global\\DeltaForceCleaner_SingleInstance"


def _acquire_single_instance() -> bool:
    """Refuse to open a second window; focus is better handled by the OS."""
    try:
        handle = ctypes.windll.kernel32.CreateMutexW(None, True, MUTEX_NAME)
        if not handle:
            return True
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            return False
        return True
    except Exception:
        return True


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        from cli import main as cli_main

        return cli_main(sys.argv[2:])

    if not _acquire_single_instance():
        try:
            ctypes.windll.user32.MessageBoxW(
                None, "三角洲行动 卸载工具已经在运行了。", "三角洲行动 卸载工具", 0x40
            )
        except Exception:
            pass
        return 0

    from gui import main as gui_main

    gui_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
