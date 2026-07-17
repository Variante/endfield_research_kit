@echo off
setlocal

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="/h" goto :help
if /I "%~1"=="help" goto :help

set "BUILD_UPDATES_ARGS="
set "SKIP_ASSET_UPDATES=0"
set "SKIP_AUDIO_UPDATES=0"

if exist "%~dp0endfield_paths.bat" call "%~dp0endfield_paths.bat"
if errorlevel 1 exit /b %errorlevel%
if defined ENDFIELD_GAME_ROOT set "BUILD_UPDATES_ARGS=%BUILD_UPDATES_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_PREVIOUS_EXPORT_ROOT set "BUILD_UPDATES_ARGS=%BUILD_UPDATES_ARGS% --previous-export-root "%ENDFIELD_PREVIOUS_EXPORT_ROOT%""
if defined ENDFIELD_EXPORT_ROOT set "BUILD_UPDATES_ARGS=%BUILD_UPDATES_ARGS% --export-root "%ENDFIELD_EXPORT_ROOT%""

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
if /I "%~1"=="--include-audio-updates" (
  set "SKIP_AUDIO_UPDATES=0"
  shift
  goto :parse_args
)
if /I "%~1"=="--skip-audio-updates" (
  set "SKIP_AUDIO_UPDATES=1"
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
rem - optionally skip decoded audio asset comparison while keeping other assets
rem - optionally prune previous-export files copied unchanged into the current export
rem - write webui/data/updates/latest.json for the Updates tab
if "%SKIP_ASSET_UPDATES%"=="1" (
  set "BUILD_UPDATES_ARGS=%BUILD_UPDATES_ARGS% --skip-asset-updates"
)
if "%SKIP_AUDIO_UPDATES%"=="1" (
  set "BUILD_UPDATES_ARGS=%BUILD_UPDATES_ARGS% --skip-audio-updates"
)

python .\scripts\build_updates.py %BUILD_UPDATES_ARGS%
if errorlevel 1 exit /b %errorlevel%

endlocal
exit /b 0

:help
echo Usage: build_updates.bat [--init-build] [--skip-asset-updates] [--skip-audio-updates] [build_updates.py options]
echo.
echo Builds webui\data\updates\latest.json from previous/current exported trees.
echo By default it compares the roots from endfield_paths.bat
echo (export_1d2 to export_full unless changed) for WebUI-facing text JSON
echo plus exported image/model/video/audio assets.
echo.
echo   --init-build             Alias for build_updates.py --baseline-only.
echo   --include-asset-updates  Compatibility flag; assets are included by default.
echo   --skip-asset-updates     Compare only WebUI-facing text JSON.
echo   --include-audio-updates  Compatibility flag; audio is included by default.
echo   --skip-audio-updates     Compare text plus image/model/video assets, skipping audio.
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
echo.
echo Compare any two already extracted versions and build the Updates page:
echo   build_updates.bat --previous-export-root "D:\exports\Endfield_old" --export-root "D:\exports\Endfield_new" --refresh-previous-export-baseline
echo.
echo Output:
echo   webui\data\updates\latest.json
echo   reports\updates\game-data-change-summary.json and .md
echo.
echo build_updates_by_patch.bat is the installed-VFS patch workflow; it can
echo detect, stage, archive, publish export_full, and invoke this feed builder.
echo Use --export-root and --previous-export-root to change the compared export trees.
echo For repeated runs, edit endfield_paths.bat instead.
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
