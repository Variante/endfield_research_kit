@echo off
setlocal

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="/h" goto :help
if /I "%~1"=="help" goto :help

set "EXPORT_ARGS="
set "EXPORT_FROM_GAME=0"

:parse_args
if "%~1"=="" goto :parsed_args
if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="/h" goto :help
if /I "%~1"=="help" goto :help
if /I "%~1"=="--export-from-game" (
  set "EXPORT_FROM_GAME=1"
  shift
  goto :parse_args
)
set "EXPORT_ARGS=%EXPORT_ARGS% "%~1""
shift
goto :parse_args

:parsed_args
rem Asset export/build pipeline:
rem - rebuild indexes from existing decoded assets by default
rem - export from the installed game only when explicitly requested
rem - skip structured story data and AnimeStudio by default
rem - build the WebUI Assets tab indexes and compact story media lookup
if "%EXPORT_FROM_GAME%"=="0" goto :skip_export_full
python .\scripts\export_full_from_game.py --skip-structured --animestudio-scope assets --animestudio-stages convert_by_type json_by_type %EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :after_export_full

:skip_export_full
echo [export_assets.bat] Reusing existing decoded assets; pass --export-from-game to refresh from installed game data.

:after_export_full

python .\scripts\build_assets.py
if errorlevel 1 exit /b %errorlevel%

endlocal
exit /b 0

:help
echo Usage: export_assets.bat [--export-from-game] [export_full_from_game.py options]
echo.
echo Rebuilds WebUI Assets tab indexes plus the compact Story media lookup.
echo The heavier AnimeStudio image/model/animation decode is opt-in.
echo Story/reference data is handled by export.bat; audio can be refreshed with scripts\build_audio.py.
echo.
echo   --export-from-game    Run AnimeStudio image/model/animation conversion and JSON export.
echo.
echo Other arguments are passed to scripts\export_full_from_game.py when
echo --export-from-game is present.
echo.
endlocal
exit /b 0
