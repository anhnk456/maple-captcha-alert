@echo off
title Maple CAPTCHA Alert
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) and sys.maxsize > 2**32 else 1)"
    if errorlevel 1 (
        echo [LOI] Can Python 3.11 hoac 3.12 ban 64-bit va them Python vao PATH.
        pause
        exit /b 1
    )
    echo Dang tao moi truong Python .venv...
    python -m venv .venv
    if errorlevel 1 (
        echo [LOI] Khong tao duoc .venv. Kiem tra Python va quyen ghi thu muc.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" -c "import importlib.util, sys; missing = [name for name in ('cv2', 'mss', 'numpy') if importlib.util.find_spec(name) is None]; print('Thieu thu vien: ' + ', '.join(missing)) if missing else None; sys.exit(3 if missing else 0)"
set "DEPENDENCY_STATUS=%ERRORLEVEL%"
if "%DEPENDENCY_STATUS%"=="3" (
    echo Dang cai thu vien. Lan dau can ket noi Internet...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [LOI] Cai thu vien that bai. Kiem tra Internet va loi o tren.
        pause
        exit /b 1
    )
) else (
    if not "%DEPENDENCY_STATUS%"=="0" (
        echo [LOI] Khong kiem tra duoc thu vien trong .venv.
        pause
        exit /b 1
    )
)
echo Maple CAPTCHA Alert - Canh bao bang 5 tieng beep.
echo Giu cua so nay mo de theo doi trang thai. Nhan Ctrl+C de dung.
echo.
".venv\Scripts\python.exe" -u "main.py" monitor --window MapleStory %*
set "EXIT_CODE=%ERRORLEVEL%"
pause
exit /b %EXIT_CODE%
