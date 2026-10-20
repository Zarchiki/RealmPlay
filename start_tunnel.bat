@echo off
setlocal
title RealmPlay Cloudflare Remote Play Tunnel
cd /d "%~dp0"

set "CF_EXE=%~dp0runtime\cloudflared\cloudflared.exe"
if not exist "%CF_EXE%" set "CF_EXE=cloudflared"

if not exist "logs" mkdir "logs"

echo ========================================================
echo       RealmPlay Remote Play (Cloudflare Quick Tunnel)
echo ========================================================
echo Using: %CF_EXE%
echo Starting tunnel to local port 8000...
echo.
echo An HTTPS public URL (e.g. https://xxxx.trycloudflare.com) 
echo will appear below in a few seconds.
echo ========================================================
echo.

"%CF_EXE%" tunnel --url http://127.0.0.1:8000 --logfile "%~dp0logs\tunnel.log"
pause
