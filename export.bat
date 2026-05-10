@echo off
setlocal

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help

rem WebUI export/build pipeline:
rem - export structured data and AnimeStudio outputs used by Story/Reference/Assets
rem - skip raw_vfs and source inventory because the WebUI does not require them
rem - build the game-data update feed
rem - build only CN story/reference data by default
rem - build the asset index
python .\scripts\export_full_from_game.py --skip-raw-vfs --skip-source-inventory %*
if errorlevel 1 exit /b %errorlevel%

python .\scripts\webui\build_updates.py
if errorlevel 1 exit /b %errorlevel%

python .\scripts\webui\build_story.py --languages CN --default-language CN
if errorlevel 1 exit /b %errorlevel%

python .\scripts\webui\build_assets.py
if errorlevel 1 exit /b %errorlevel%

endlocal
exit /b 0

:help
echo Usage: export.bat [export_full_from_game.py options]
echo.
echo Runs the WebUI-focused export/build pipeline. Story/reference output is CN only.
echo.
python .\scripts\export_full_from_game.py --help
if errorlevel 1 (
  set "ERR=%errorlevel%"
  endlocal
  exit /b %ERR%
)
endlocal
exit /b 0
