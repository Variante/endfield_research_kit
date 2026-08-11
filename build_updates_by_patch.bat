@echo off
setlocal

rem Detects a game patch in the installed Endfield files, produces the new
rem export, and builds the WebUI Updates tab from what actually changed.
rem
rem   build_updates_by_patch.bat               apply a detected patch
rem   build_updates_by_patch.bat --check       report changes, write nothing
rem   build_updates_by_patch.bat --first-time  record the installed version
rem   build_updates_by_patch.bat --help        all options

set "MODE_ARGS="
set "OPTION_ARGS="
set "EXTRA_ARGS="
set "MODE_COUNT=0"

if exist "%~dp0endfield_paths.bat" call "%~dp0endfield_paths.bat"
if errorlevel 1 exit /b %errorlevel%

call :is_help "%~1"
if not errorlevel 1 goto :help

:parse_args
if "%~1"=="" goto :compose
call :is_help "%~1"
if not errorlevel 1 goto :help

rem Modes, one per run.
if /I "%~1"=="--update" goto :mode_update
if /I "%~1"=="--apply" goto :mode_update
if /I "%~1"=="--check" goto :mode_check
if /I "%~1"=="--first-time" goto :mode_first_time
if /I "%~1"=="--init-baseline" goto :mode_first_time
if /I "%~1"=="--init-current-version" goto :mode_first_time
if /I "%~1"=="--baseline-current" goto :mode_first_time

rem Asset scope, named the same way as export.bat.
if /I "%~1"=="--focused-assets" goto :assets_focused
if /I "%~1"=="--default-assets" goto :assets_default
if /I "%~1"=="--debug-assets" goto :assets_debug
if /I "%~1"=="--asset-mode" goto :assets_explicit

rem Worker limit, named the same way as export.bat.
if /I "%~1"=="--asset-jobs" goto :opt_jobs
if /I "%~1"=="--jobs" goto :opt_jobs
if /I "%~1"=="--animestudio-jobs" goto :opt_jobs

rem Anything else, including its value, goes to the workflow script.
set "EXTRA_ARGS=%EXTRA_ARGS% "%~1""
shift
goto :parse_args

:mode_update
set /a MODE_COUNT+=1
set "MODE_ARGS= --apply"
shift
goto :parse_args

:mode_check
set /a MODE_COUNT+=1
set "MODE_ARGS= --check"
shift
goto :parse_args

:mode_first_time
set /a MODE_COUNT+=1
set "MODE_ARGS= --init-baseline"
shift
goto :parse_args

:assets_focused
set "OPTION_ARGS=%OPTION_ARGS% --asset-mode focused"
shift
goto :parse_args

:assets_default
set "OPTION_ARGS=%OPTION_ARGS% --asset-mode default"
shift
goto :parse_args

:assets_debug
set "OPTION_ARGS=%OPTION_ARGS% --asset-mode debug"
shift
goto :parse_args

:assets_explicit
if "%~2"=="" goto :missing_asset_mode
call :is_asset_mode "%~2"
if errorlevel 1 goto :bad_asset_mode
set "OPTION_ARGS=%OPTION_ARGS% --asset-mode %~2"
shift
shift
goto :parse_args

:opt_jobs
if "%~2"=="" goto :missing_jobs
set "OPTION_ARGS=%OPTION_ARGS% --animestudio-jobs %~2"
shift
shift
goto :parse_args

:compose
if %MODE_COUNT% GTR 1 (
  echo Choose one mode: --update, --check, or --first-time.
  exit /b 2
)
if not defined MODE_ARGS set "MODE_ARGS= --apply"

set "PATH_ARGS="
if defined ENDFIELD_GAME_ROOT set "PATH_ARGS=%PATH_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_EXPORT_ROOT set "PATH_ARGS=%PATH_ARGS% --export-root "%ENDFIELD_EXPORT_ROOT%""
if defined ENDFIELD_PREVIOUS_EXPORT_ROOT set "PATH_ARGS=%PATH_ARGS% --previous-export-root "%ENDFIELD_PREVIOUS_EXPORT_ROOT%""

python .\scripts\game_data_update_workflow.py%MODE_ARGS%%PATH_ARGS%%OPTION_ARGS%%EXTRA_ARGS%
if errorlevel 1 exit /b %errorlevel%

endlocal
exit /b 0

:missing_asset_mode
echo Missing value for --asset-mode. Expected focused, default, or debug.
exit /b 2

:bad_asset_mode
echo Invalid asset mode: "%~2"
echo Expected focused, default, or debug.
exit /b 2

:missing_jobs
echo Missing value for %~1. Expected a worker count, for example 8.
exit /b 2

:is_asset_mode
if /I "%~1"=="focused" exit /b 0
if /I "%~1"=="default" exit /b 0
if /I "%~1"=="debug" exit /b 0
exit /b 1

:is_help
if /I "%~1"=="--help" exit /b 0
if /I "%~1"=="-h" exit /b 0
if /I "%~1"=="/?" exit /b 0
if /I "%~1"=="/h" exit /b 0
if /I "%~1"=="help" exit /b 0
exit /b 1

:help
echo Usage: build_updates_by_patch.bat [--update ^| --check ^| --first-time] [options]
echo.
echo Use this after the installed game updates itself. It compares the
echo installed files against the last recorded version, exports only what
echo changed, archives the old export, publishes the new export_full,
echo rebuilds the WebUI, and builds the Updates tab.
echo.
echo Modes, one per run:
echo   --update       Default. Do the whole job above. If nothing changed,
echo                  the exports, archive and Updates feed are left alone.
echo   --check        Only report what changed. Writes nothing.
echo                  Safe to run any time.
echo   --first-time   Record the currently installed version as the starting
echo                  point. Run this once, before any patch arrives; no
echo                  previous export is needed.
echo.
echo Options:
echo   --focused-assets   Narrowest asset refresh when changed data touches assets.
echo   --default-assets   Default asset refresh.
echo   --debug-assets     Broadest asset refresh, with diagnostics.
echo   --asset-jobs N     AnimeStudio worker limit. Default is 8. Lower it if
echo                      the machine runs out of memory.
echo   --help             This text.
echo.
echo Examples:
echo   build_updates_by_patch.bat --check
echo   build_updates_by_patch.bat
echo   build_updates_by_patch.bat --focused-assets --asset-jobs 4
echo.
echo Folders come from endfield_paths.bat:
echo   installed game: %ENDFIELD_GAME_ROOT%
echo   current export: %ENDFIELD_EXPORT_ROOT%
echo   archive target: %ENDFIELD_PREVIOUS_EXPORT_ROOT%
echo.
echo Notes:
echo   If the archive target already exists, a dated sibling folder is used
echo   instead, so an existing archive is never overwritten.
echo   The recorded version advances only after every step succeeds.
echo   build_updates.bat is the other workflow: use it to compare two
echo   exports you already have on disk.
echo   The older --apply, --init-baseline, --init-current-version,
echo   --baseline-current, --asset-mode MODE and --animestudio-jobs N
echo   spellings still work.
echo   Advanced options are passed through to
echo   scripts\game_data_update_workflow.py. Run
echo   "python scripts\game_data_update_workflow.py --help" to see them.
echo.
endlocal
exit /b 0
