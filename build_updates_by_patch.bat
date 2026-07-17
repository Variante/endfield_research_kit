@echo off
setlocal

if exist "%~dp0endfield_paths.bat" call "%~dp0endfield_paths.bat"
if errorlevel 1 exit /b %errorlevel%

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="help" goto :help

set "WORKFLOW_ARGS="
set "MODE_SET=0"
if defined ENDFIELD_GAME_ROOT set "WORKFLOW_ARGS=%WORKFLOW_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_EXPORT_ROOT set "WORKFLOW_ARGS=%WORKFLOW_ARGS% --export-root "%ENDFIELD_EXPORT_ROOT%""
if defined ENDFIELD_PREVIOUS_EXPORT_ROOT set "WORKFLOW_ARGS=%WORKFLOW_ARGS% --previous-export-root "%ENDFIELD_PREVIOUS_EXPORT_ROOT%""

if "%~1"=="" goto :run

:parse_args
if "%~1"=="" goto :run
if /I "%~1"=="--apply" set "MODE_SET=1"
if /I "%~1"=="--check" set "MODE_SET=1"
if /I "%~1"=="--init-baseline" set "MODE_SET=1"
if /I "%~1"=="--baseline-current" set "MODE_SET=1"
if /I "%~1"=="--init-current-version" (
  set "MODE_SET=1"
  set "WORKFLOW_ARGS=%WORKFLOW_ARGS% --init-baseline"
) else (
  set "WORKFLOW_ARGS=%WORKFLOW_ARGS% "%~1""
)
shift
goto :parse_args

:run
if "%MODE_SET%"=="0" set "WORKFLOW_ARGS=%WORKFLOW_ARGS% --apply"
python .\scripts\game_data_update_workflow.py %WORKFLOW_ARGS%
if errorlevel 1 exit /b %errorlevel%

endlocal
exit /b 0

:help
echo Usage: build_updates_by_patch.bat [--apply ^| --check ^| --init-baseline] [options]
echo.
echo Tracks original installed-game VFS logical files and builds a complete
echo latest export_full plus the WebUI Updates feed from changed data.
echo.
echo   --apply                  Default. Detect changes; on logical no-change,
echo                            leave the baseline, exports, archive, and feed
echo                            untouched. On change, clone the current export
echo                            into staging, selectively export changed direct
echo                            VFS files, refresh affected asset/audio scopes,
echo                            archive the previous export, publish the latest
echo                            export_full, rebuild WebUI data, and build Updates.
echo   --check                  Detection only; never changes published state.
echo   --init-baseline          Seed the original-VFS baseline from only the
echo                            current installed version and current export_full.
echo   --init-current-version   Alias for --init-baseline.
echo   --baseline-current       Alias for --init-baseline.
echo   --asset-mode MODE        webui, full, or debug; default full.
echo   --animestudio-jobs N     Worker limit for asset-affecting patches.
echo.
echo Paths default from endfield_paths.bat. If the configured previous-export
echo destination already exists, a snapshot-suffixed sibling archive is used.
echo The source baseline advances only after staging, rotation, WebUI rebuild,
echo and Updates feed generation all succeed.
echo.
python .\scripts\game_data_update_workflow.py --help
endlocal
exit /b 0
