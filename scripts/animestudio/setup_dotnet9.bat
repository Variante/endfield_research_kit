@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_dotnet9.ps1" %*
exit /b %errorlevel%
