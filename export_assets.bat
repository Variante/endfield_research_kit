@echo off
setlocal

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help

set "EXPORT_ARGS="
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
set "EXPORT_ARGS=%EXPORT_ARGS% "%~1""
shift
goto :parse_args

:parsed_args
rem Asset export/build pipeline:
rem - skip structured story data
rem - export AnimeStudio image/model/animation conversions and full asset metadata
rem - build the WebUI Assets tab indexes and compact story media lookup
if "%SKIP_EXPORT_FULL%"=="1" goto :skip_export_full
python .\scripts\export_full_from_game.py --skip-structured --animestudio-scope assets --animestudio-stages convert_by_type json_by_type %EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :after_export_full

:skip_export_full
echo [export_assets.bat] Skipping scripts\export_full_from_game.py; rebuilding asset indexes from existing decoded assets.

:after_export_full

python .\scripts\build_assets.py
if errorlevel 1 exit /b %errorlevel%

endlocal
exit /b 0

:help
echo Usage: export_assets.bat [--skip-export-full] [--game-root Endfield_Data] [--animestudio-jobs N] [export_full_from_game.py options]
echo.
echo Runs the heavier image/model/animation asset decode and rebuilds WebUI asset indexes.
echo Story/reference data is handled by export.bat.
echo.
echo   --skip-export-full    Reuse existing decoded assets and only rebuild asset indexes.
echo   --game-root PATH      Use a non-default installed Endfield_Data path.
echo   --animestudio-jobs N  Maximum parallel AnimeStudio CLI processes for per-type export.
echo.
python .\scripts\export_full_from_game.py --help
if errorlevel 1 (
  set "ERR=%errorlevel%"
  endlocal
  exit /b %ERR%
)
endlocal
exit /b 0
