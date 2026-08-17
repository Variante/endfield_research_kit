@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0capture_m23_source_dxcap.ps1" %*
exit /b %ERRORLEVEL%
