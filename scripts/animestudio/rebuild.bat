@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0rebuild.ps1" %*
exit /b %errorlevel%
