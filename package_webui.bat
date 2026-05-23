@echo off
setlocal

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="/h" goto :help
if /I "%~1"=="help" goto :help

python .\scripts\package_webui.py %*
if errorlevel 1 exit /b %errorlevel%

endlocal
exit /b 0

:help
echo Usage: package_webui.bat [package_webui.py options]
echo.
echo Creates split shareable WebUI zips: a story/code/emoji/audio package and
echo a companion assets package for larger story images and videos.
echo.
echo Common options:
echo   -o, --output PATH        Primary story zip path.
echo   --assets-output PATH     Companion assets zip path.
echo   --include-asset-browser  Keep the asset-browser UI files in the package.
echo   --dry-run                Print the package plan without writing zips.
echo.
python .\scripts\package_webui.py --help
if errorlevel 1 (
  set "ERR=%errorlevel%"
  endlocal
  exit /b %ERR%
)
endlocal
exit /b 0
