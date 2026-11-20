@echo off
chcp 65001 >nul
cd /d "%~dp0"
where pythonw >nul 2>nul
if errorlevel 1 (
  echo 未找到 pythonw.exe，请先安装 Python 3.9+
  pause
  exit /b 1
)
start "" pythonw "%~dp0main.py"
