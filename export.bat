@echo off
setlocal

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help

set "EXPORT_ARGS="
set "BUILD_UPDATES_ARGS="

:parse_args
if "%~1"=="" goto :parsed_args
if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="--skip-asset-updates" (
  set "BUILD_UPDATES_ARGS=%BUILD_UPDATES_ARGS% --skip-asset-updates"
  shift
  goto :parse_args
)
if /I "%~1"=="--skip-exported-assets" (
  set "BUILD_UPDATES_ARGS=%BUILD_UPDATES_ARGS% --skip-asset-updates"
  shift
  goto :parse_args
)
if /I "%~1"=="--baseline-only-updates" (
  set "BUILD_UPDATES_ARGS=%BUILD_UPDATES_ARGS% --baseline-only"
  shift
  goto :parse_args
)
if /I "%~1"=="--init-build" (
  set "BUILD_UPDATES_ARGS=%BUILD_UPDATES_ARGS% --baseline-only"
  shift
  goto :parse_args
)
set "EXPORT_ARGS=%EXPORT_ARGS% "%~1""
shift
goto :parse_args

:parsed_args
rem WebUI export/build pipeline:
rem - export structured data and AnimeStudio outputs used by Story/Reference/Assets
rem - skip raw_vfs and source inventory because the WebUI does not require them
rem - build the game-data update feed
rem - build only CN story/reference data by default
rem - build the asset index
python .\scripts\export_full_from_game.py --skip-raw-vfs --skip-source-inventory %EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%

python .\scripts\recover_dialog_id_registry.py --quiet
if errorlevel 1 exit /b %errorlevel%

python .\scripts\webui\build_story_source_links.py
if errorlevel 1 exit /b %errorlevel%

python .\scripts\webui\build_updates.py %BUILD_UPDATES_ARGS%
if errorlevel 1 exit /b %errorlevel%

python .\scripts\webui\build_story.py --languages CN --default-language CN
if errorlevel 1 exit /b %errorlevel%

python .\scripts\webui\build_assets.py
if errorlevel 1 exit /b %errorlevel%

endlocal
exit /b 0

:help
echo Usage: export.bat [--init-build] [--skip-asset-updates] [export_full_from_game.py options]
echo.
echo Runs the WebUI-focused export/build pipeline. Story/reference output is CN only.
echo.
echo   --init-build          Write an empty baseline Updates feed and skip asset diffing.
echo   --skip-asset-updates  Skip exported asset update diffing for a fast initial build.
echo.
python .\scripts\export_full_from_game.py --help
if errorlevel 1 (
  set "ERR=%errorlevel%"
  endlocal
  exit /b %ERR%
)
endlocal
exit /b 0
