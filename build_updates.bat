@echo off
setlocal

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help

set "BUILD_UPDATES_ARGS="
set "SKIP_ASSET_UPDATES=1"

:parse_args
if "%~1"=="" goto :parsed_args
if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="--init-build" (
  set "BUILD_UPDATES_ARGS=%BUILD_UPDATES_ARGS% --baseline-only"
  shift
  goto :parse_args
)
if /I "%~1"=="--include-asset-updates" (
  set "SKIP_ASSET_UPDATES=0"
  shift
  goto :parse_args
)
if /I "%~1"=="--skip-asset-updates" (
  set "SKIP_ASSET_UPDATES=1"
  shift
  goto :parse_args
)
set "BUILD_UPDATES_ARGS=%BUILD_UPDATES_ARGS% "%~1""
shift
goto :parse_args

:parsed_args
rem Updates pipeline:
rem - compare the saved previous export with the current export_full tree
rem - write webui/data/updates/latest.json for the Updates tab
rem - skip exported asset diffs by default; opt in after refreshing heavy assets
if "%SKIP_ASSET_UPDATES%"=="1" (
  set "BUILD_UPDATES_ARGS=%BUILD_UPDATES_ARGS% --skip-asset-updates"
)

python .\scripts\build_updates.py %BUILD_UPDATES_ARGS%
if errorlevel 1 exit /b %errorlevel%

endlocal
exit /b 0

:help
echo Usage: build_updates.bat [--init-build] [--include-asset-updates] [build_updates.py options]
echo.
echo Builds webui\data\updates\latest.json from old/new exported game-data trees.
echo.
echo   --init-build             Alias for build_updates.py --baseline-only.
echo   --include-asset-updates  Also diff exported image/model/video assets.
echo                            By default the wrapper passes --skip-asset-updates.
echo.
python .\scripts\build_updates.py --help
if errorlevel 1 (
  set "ERR=%errorlevel%"
  endlocal
  exit /b %ERR%
)
endlocal
exit /b 0
