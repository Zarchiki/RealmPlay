@echo off
setlocal EnableExtensions
title Allow RealmPlay through Windows Firewall

rem Re-launch with Administrator rights when needed.
net session >nul 2>&1
if errorlevel 1 (
  echo Requesting Administrator permission...
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

set "RP_PY=K:\text-generation-webui\installer_files\env\python.exe"
set "CF_EXE=%~dp0runtime\cloudflared\cloudflared.exe"

if not exist "%RP_PY%" (
  echo ERROR: RealmPlay Python was not found:
  echo %RP_PY%
  pause
  exit /b 1
)

if not exist "%CF_EXE%" (
  echo ERROR: cloudflared.exe was not found:
  echo %CF_EXE%
  pause
  exit /b 1
)

echo Adding or enabling RealmPlay Firewall rules...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $rp='K:\text-generation-webui\installer_files\env\python.exe'; $cf='%~dp0runtime\cloudflared\cloudflared.exe'; $rules=@(@{Name='RealmPlay Server (Inbound TCP 8000)'; Direction='Inbound'; Program=$rp; Protocol='TCP'; LocalPort='8000'; Profile='Private'; Description='Allow inbound LAN access to RealmPlay on TCP port 8000.'}, @{Name='RealmPlay Cloudflare Tunnel (Outbound)'; Direction='Outbound'; Program=$cf; Protocol='Any'; LocalPort=$null; Profile='Any'; Description='Allow RealmPlay cloudflared to create outbound Cloudflare Quick Tunnels.'}); foreach($rule in $rules){$existing=Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue; if($existing){Set-NetFirewallRule -DisplayName $rule.Name -Enabled True -Action Allow -Profile $rule.Profile | Out-Null}else{$firewallArgs=@{DisplayName=$rule.Name; Description=$rule.Description; Direction=$rule.Direction; Program=$rule.Program; Action='Allow'; Profile=$rule.Profile}; if($rule.Protocol -ne 'Any'){$firewallArgs.Protocol=$rule.Protocol; $firewallArgs.LocalPort=$rule.LocalPort}; New-NetFirewallRule @firewallArgs | Out-Null}}; Write-Host 'Firewall rules are enabled.'"

if errorlevel 1 (
  echo ERROR: Windows Firewall could not add the rules.
  pause
  exit /b 1
)

echo.
echo Done.
echo - RealmPlay: inbound TCP 8000, Private network only
echo - Cloudflare Tunnel: outbound access only
pause
