@echo off
chcp 65001 >nul
cd /d "%~dp0"
where pythonw >nul 2>nul
if errorlevel 1 (
  echo Python 3.9+ (with Tkinter) is required. https://www.python.org/downloads/
  pause
  exit /b 1
)
start "" pythonw "%~dp0main.py"