@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set LOG=nhatky_tudong.txt
echo. >> %LOG%
echo ================ %date% %time% ================ >> %LOG%

echo [1/4] Duyet clip ghi hinh hom nay (anh net)... >> %LOG%
python -m app.main --duyet-clip --ngay hom-nay --khong-mo >> %LOG% 2>&1

echo [2/4] Sinh lai bao cao gop... >> %LOG%
python -m app.main --trang-chu >> %LOG% 2>&1

echo [3/4] Chi giu 3 ngay gan nhat tren GitHub... >> %LOG%
python -m app.git_sync >> %LOG% 2>&1

echo [4/4] Day len GitHub... >> %LOG%
git add -A >> %LOG% 2>&1
git commit -m "Tu dong cap nhat bao cao %date% %time%" >> %LOG% 2>&1
git push >> %LOG% 2>&1

echo Xong. >> %LOG%
