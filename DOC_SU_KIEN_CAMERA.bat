@echo off
chcp 65001 >nul
cd /d "%~dp0"
set /p NGAY=Nhap ngay (Enter = hom nay, vd 23 hoac 2026-08-23): 
if "%NGAY%"=="" set NGAY=hom-nay
python -m app.main --su-kien --ngay %NGAY%
pause
