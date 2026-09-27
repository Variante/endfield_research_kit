@echo off
setlocal

rem Builds WebUI pages, grouped by page. Pages and what each one extracts
rem are declared in scripts\webui\pages.py; this wrapper only loads the
rem local path defaults and hands every argument to scripts\webui\export.py.
rem
rem   export.bat                        rebuild every page from the current export
rem   export.bat --from-game            extract what every page reads, then build
rem   export.bat story --from-game      the lean Story/Text extraction and build
rem   export.bat map audio --from-game  only what Map and Audio read
rem   export.bat debug --from-game      every structured block and Unity class
rem   export.bat --changed-only         apply changed structured files, build all
rem   export.bat --help                 every option

rem endfield_paths.bat supplies ENDFIELD_GAME_ROOT and ENDFIELD_EXPORT_ROOT;
rem --game-root still overrides the installed client for one run.
if exist "%~dp0endfield_paths.bat" call "%~dp0endfield_paths.bat"
if errorlevel 1 exit /b %errorlevel%

pushd "%~dp0" || exit /b 1
python -m scripts.webui.export %*
set "EXPORT_EXIT=%errorlevel%"
popd
endlocal & exit /b %EXPORT_EXIT%
