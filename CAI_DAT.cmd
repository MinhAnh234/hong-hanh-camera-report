@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

echo ============================================================
echo   CAI DAT APP CHUP ANH XE - HONG HANH COMPANY
echo ============================================================
echo.

:: --- 1. Tim Python ---
set PY=
where py >nul 2>&1 && set PY=py -3
if not defined PY (where python >nul 2>&1 && set PY=python)
if not defined PY (
  echo [LOI] Chua cai Python.
  echo       Tai tai: https://www.python.org/downloads/windows/
  echo       Khi cai NHO TICH o "Add python.exe to PATH".
  echo.
  pause
  exit /b 1
)
echo [OK] Tim thay Python: %PY%
echo.

:: --- 2. Cai thu vien ---
echo Dang cai thu vien can thiet (lan dau co the mat vai phut)...
%PY% -m pip install --upgrade pip --disable-pip-version-check --quiet
%PY% -m pip install --disable-pip-version-check ^
     "opencv-python==4.10.0.84" numpy mss pywin32 pillow winsdk
if errorlevel 1 (
  echo [LOI] Cai thu vien that bai. Kiem tra ket noi mang roi chay lai.
  pause
  exit /b 1
)
echo.

:: --- 3. Dang ky pywin32 (can cho mot so may) ---
for /f "delims=" %%i in ('%PY% -c "import sysconfig;print(sysconfig.get_paths()['scripts'])"') do set SCRIPTS=%%i
if exist "%SCRIPTS%\pywin32_postinstall.py" (
  %PY% "%SCRIPTS%\pywin32_postinstall.py" -install >nul 2>&1
)

:: --- 4. Kiem tra + tai mo hinh nhan dang ---
%PY% -m app.cai_dat
set KETQUA=%errorlevel%
echo.

if "%KETQUA%"=="0" (
  echo Ban co muon tao lich tu dong quet moi 3 tieng khong?
  choice /C YN /N /M "  Bam Y de tao, N de bo qua: "
  if errorlevel 2 goto :xong
  schtasks /Create /TN "HongHanh - Quet camera moi 3 gio" ^
      /TR "\"%~dp0TU_DONG_QUET.bat\"" /SC HOURLY /MO 3 /ST 08:00 /F
  echo [OK] Da tao lich. Xem bang: schtasks /Query /TN "HongHanh - Quet camera moi 3 gio"
)

:xong
echo.
echo ============================================================
pause
endlocal
