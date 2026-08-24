@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m app.main --nen --phut 0
pause
