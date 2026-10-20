@echo off
title RealmPlay Launcher (Port 8000)
cd /d "%~dp0"
echo ========================================================
echo               RealmPlay AI Roleplay Server
echo ========================================================
set "RP_PY=python"
if exist "venv\Scripts\python.exe" (
    set "RP_PY=venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "RP_PY=.venv\Scripts\python.exe"
)

if not exist "config.json" (
    if exist "config.example.json" (
        echo [INFO] config.json not found. Creating from config.example.json ...
        copy "config.example.json" "config.json" >nul
    )
)

echo Starting server on http://localhost:8000 ...
rem Do not use --reload here: its file watcher restarts the worker when the LLM log changes,
rem which also terminates the managed llama-server process.
:start_server
"%RP_PY%" -m uvicorn server:app --host 0.0.0.0 --port 8000
set "RP_EXIT_CODE=%ERRORLEVEL%"

if "%RP_EXIT_CODE%"=="75" (
    echo.
    echo Closing current console and launching new RealmPlay window...
    start "RealmPlay Launcher (Port 8000)" "%~f0"
    exit
)

if "%RP_EXIT_CODE%"=="0" exit /b 0
echo.
echo ERROR: RealmPlay stopped with exit code %RP_EXIT_CODE%.
echo Review the error above, then press any key to close this window.
pause >nul
exit /b %RP_EXIT_CODE%
