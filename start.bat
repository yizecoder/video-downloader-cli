@echo off
setlocal
cd /d "%~dp0"
chcp 65001 > nul
set PYTHONUTF8=1

python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.10 or newer was not found.
    pause
    exit /b 1
)

python main.py %*
set EXIT_CODE=%ERRORLEVEL%
echo.
pause
exit /b %EXIT_CODE%
