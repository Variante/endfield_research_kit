@echo off
setlocal

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="/h" goto :help
if /I "%~1"=="help" goto :help

set "BUILD_UPDATES_ARGS="
set "SKIP_ASSET_UPDATES=0"

:parse_args
if "%~1"=="" goto :parsed_args
if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="/h" goto :help
if /I "%~1"=="help" goto :help
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
rem - compare WebUI-facing text JSON in the saved previous/current exports
rem - compare exported image/model/video/audio assets by default
rem - prune previous-export files already copied unchanged into the current export
rem - write webui/data/updates/latest.json for the Updates tab
if "%SKIP_ASSET_UPDATES%"=="1" (
  set "BUILD_UPDATES_ARGS=%BUILD_UPDATES_ARGS% --skip-asset-updates"
)

python .\scripts\build_updates.py %BUILD_UPDATES_ARGS%
if errorlevel 1 exit /b %errorlevel%

endlocal
exit /b 0

:help
echo Usage: build_updates.bat [--init-build] [--skip-asset-updates] [build_updates.py options]
echo.
echo Builds webui\data\updates\latest.json from previous/current exported trees.
echo By default it compares export_1d2 to export_full for WebUI-facing text JSON
echo plus exported image/model/video/audio assets.
echo.
echo   --init-build             Alias for build_updates.py --baseline-only.
echo   --include-asset-updates  Compatibility flag; assets are included by default.
echo   --skip-asset-updates     Compare only WebUI-facing text JSON.
echo   --game-root PATH         Installed Endfield_Data directory used only for
echo                            optional decoded-impact mapping.
echo   --hash-asset-updates     Hash asset contents; slower, catches same-size changes.
echo   --prune-previous-export-untracked
echo                            Delete previous-export files that are byte-identical
echo                            at the same relative path in the current export.
echo   --dry-run-prune-previous-export-untracked
echo                            Report prune deletions without deleting files.
echo.
echo Useful after replacing the saved previous export:
echo   build_updates.bat --refresh-previous-export-baseline
echo Use --export-root and --previous-export-root to change the compared export trees.
echo Most runs do not need --game-root; it is only for optional decoded-impact mapping.
echo.
python .\scripts\build_updates.py --help
if errorlevel 1 (
  set "ERR=%errorlevel%"
  endlocal
  exit /b %ERR%
)
endlocal
exit /b 0
