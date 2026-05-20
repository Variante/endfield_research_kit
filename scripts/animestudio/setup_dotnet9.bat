@echo off
setlocal

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="/h" goto :help
if /I "%~1"=="help" goto :help

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_dotnet9.ps1" %*
exit /b %errorlevel%

:help
echo Usage: scripts\animestudio\setup_dotnet9.bat [-Channel VERSION] [-InstallDir PATH] [-Force] [-DryRun]
echo.
echo Installs a local .NET SDK for tools\AnimeStudio, defaulting to channel 9.0
echo under tools\AnimeStudio\.dotnet. This wrapper is for maintaining the
echo AnimeStudio CLI used by export_assets.bat and export.bat.
echo.
echo Common examples:
echo   scripts\animestudio\setup_dotnet9.bat
echo   scripts\animestudio\setup_dotnet9.bat -Force
echo   scripts\animestudio\setup_dotnet9.bat -DryRun
echo.
endlocal
exit /b 0
