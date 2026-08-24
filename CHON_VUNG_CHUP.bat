@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m app.select_roi
pause
