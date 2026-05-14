@echo off
setlocal

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help

set "EXPORT_ARGS="
set "VERIFY_EXPORT_ARGS="
set "BUILD_UPDATES_ARGS="
set "BUILD_ASSETS_ARGS="

:parse_args
if "%~1"=="" goto :parsed_args
if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="--init-build" (
  set "BUILD_UPDATES_ARGS=%BUILD_UPDATES_ARGS% --baseline-only"
  shift
  goto :parse_args
)
if /I "%~1"=="--fast-assets" (
  set "BUILD_ASSETS_ARGS=%BUILD_ASSETS_ARGS% --fast"
  shift
  goto :parse_args
)
if /I "%~1"=="--game-root" (
  if "%~2"=="" (
    echo Missing value for --game-root.
    exit /b 2
  )
  set "EXPORT_ARGS=%EXPORT_ARGS% "%~1" "%~2""
  set "VERIFY_EXPORT_ARGS=%VERIFY_EXPORT_ARGS% "%~1" "%~2""
  set "BUILD_UPDATES_ARGS=%BUILD_UPDATES_ARGS% "%~1" "%~2""
  shift
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

python .\scripts\verify_export_freshness.py %VERIFY_EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\dialog_registry.py --quiet
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\video_bindings.py
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\source_links.py
if errorlevel 1 exit /b %errorlevel%

python .\scripts\build_updates.py %BUILD_UPDATES_ARGS%
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\build.py --languages CN --default-language CN
if errorlevel 1 exit /b %errorlevel%

python .\scripts\build_assets.py %BUILD_ASSETS_ARGS%
if errorlevel 1 exit /b %errorlevel%

endlocal
exit /b 0

:help
echo Usage: export.bat [--init-build] [--fast-assets] [--game-root Endfield_Data] [export_full_from_game.py options]
echo.
echo Runs the WebUI-focused export/build pipeline. Story/reference output is CN only.
echo Verifies export freshness before the long WebUI builders run.
echo.
echo   --init-build          Write an empty baseline Updates feed and skip asset diffing.
echo   --fast-assets         Build asset indexes but skip demo bundle zip generation.
echo   --game-root PATH      Use a non-default installed Endfield_Data path.
echo.
python .\scripts\export_full_from_game.py --help
if errorlevel 1 (
  set "ERR=%errorlevel%"
  endlocal
  exit /b %ERR%
)
endlocal
exit /b 0
