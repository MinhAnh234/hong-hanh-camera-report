@echo off
chcp 65001 >nul
cd /d "%~dp0"
set LOG=nhatky_tudong.txt
echo. >> %LOG%
echo ================ %date% %time% ================ >> %LOG%

echo [1/3] Quet su kien phuong tien hom nay... >> %LOG%

echo [2/3] Sinh lai trang chu... >> %LOG%
python -m app.main --trang-chu >> %LOG% 2>&1

echo [3/3] Day len GitHub... >> %LOG%
git add -A >> %LOG% 2>&1
git commit -m "Tu dong cap nhat bao cao %date% %time%" >> %LOG% 2>&1
git push >> %LOG% 2>&1

echo Xong. >> %LOG%
