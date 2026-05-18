@echo off
setlocal

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help

set "EXPORT_ARGS="
set "VERIFY_EXPORT_ARGS="
set "SKIP_EXPORT_FULL=0"

:parse_args
if "%~1"=="" goto :parsed_args
if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="--skip-export-full" (
  set "SKIP_EXPORT_FULL=1"
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
  shift
  shift
  goto :parse_args
)
set "EXPORT_ARGS=%EXPORT_ARGS% "%~1""
shift
goto :parse_args

:parsed_args
rem WebUI export/build pipeline:
rem - export structured data and story-only AnimeStudio outputs used by Story/Reference
rem - skip raw_vfs and source inventory because the WebUI does not require them
rem - optionally skip the export step when reusing an already fresh export_full
rem - build only CN story/reference data by default
rem - build recovered story file order for the WebUI Story sort
rem - skip image/model/animation asset decoding; use export_assets.bat for that
if "%SKIP_EXPORT_FULL%"=="1" goto :skip_export_full
python .\scripts\export_full_from_game.py --animestudio-scope story --animestudio-stages maps json_by_type %EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :after_export_full

:skip_export_full
echo [export.bat] Skipping scripts\export_full_from_game.py; verifying existing export_full before building.

:after_export_full

python .\scripts\verify_export_freshness.py %VERIFY_EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\dialog_registry.py --quiet
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\video_bindings.py
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\source_links.py
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\build.py --languages CN --default-language CN
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_recovery\build_story_order.py
if errorlevel 1 exit /b %errorlevel%

endlocal
exit /b 0

:help
echo Usage: export.bat [--skip-export-full] [--game-root Endfield_Data] [--animestudio-jobs N] [export_full_from_game.py options]
echo.
echo Runs the story-focused WebUI export/build pipeline. Story/reference output is CN only.
echo Verifies export freshness before the long WebUI builders run.
echo.
echo   --skip-export-full    Reuse existing export_full and only verify freshness before builders.
echo   --game-root PATH      Use a non-default installed Endfield_Data path.
echo   --animestudio-jobs N  Maximum parallel AnimeStudio CLI processes for per-type export.
echo.
echo Updates moved to build_updates.bat. Image/model/animation asset decoding moved to export_assets.bat.
echo.
python .\scripts\export_full_from_game.py --help
if errorlevel 1 (
  set "ERR=%errorlevel%"
  endlocal
  exit /b %ERR%
)
endlocal
exit /b 0
