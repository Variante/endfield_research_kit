@echo off
setlocal

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="/h" goto :help
if /I "%~1"=="help" goto :help

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0rebuild.ps1" %*
exit /b %errorlevel%

:help
echo Usage: scripts\animestudio\rebuild.bat [-Target CLI^|GUI^|Patcher^|AllManaged] [-Configuration Debug^|Release] [-NoRestore] [-UseSystemDotnet] [-DryRun]
echo.
echo Rebuilds the local tools\AnimeStudio managed projects used by export wrappers.
echo It prefers the repo-local .NET SDK installed by setup_dotnet9.bat.
echo.
echo Common examples:
echo   scripts\animestudio\rebuild.bat -Target CLI
echo   scripts\animestudio\rebuild.bat -Target AllManaged -Configuration Release
echo   scripts\animestudio\rebuild.bat -Target CLI -NoRestore
echo.
endlocal
exit /b 0
