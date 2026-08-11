@echo off
setlocal

rem Compares an older exported game-data folder against the current one and
rem writes the WebUI Updates tab feed plus the change reports.
rem
rem   build_updates.bat                compare the folders set in endfield_paths.bat
rem   build_updates.bat OLD NEW        compare two folders you name
rem   build_updates.bat --first-time   record a starting point, report no changes
rem   build_updates.bat --help         all options

set "OLD_EXPORT="
set "NEW_EXPORT="
set "ROOTS_GIVEN=0"
set "PRUNE_OLD=0"
set "DRY_RUN=0"
set "ROOT_ARGS="
set "MODE_ARGS="
set "EXTRA_ARGS="

if exist "%~dp0endfield_paths.bat" call "%~dp0endfield_paths.bat"
if errorlevel 1 exit /b %errorlevel%

call :is_help "%~1"
if not errorlevel 1 goto :help

rem An optional OLD NEW folder pair, which must come before any option.
call :is_option "%~1"
if not errorlevel 1 goto :parse_options
set "OLD_EXPORT=%~1"
shift
call :is_option "%~1"
if not errorlevel 1 goto :need_two_folders
set "NEW_EXPORT=%~1"
set "ROOTS_GIVEN=1"
shift

:parse_options
if "%~1"=="" goto :compose
call :is_help "%~1"
if not errorlevel 1 goto :help

rem Compare depth.
if /I "%~1"=="--text-only" goto :opt_text_only
if /I "%~1"=="--skip-asset-updates" goto :opt_text_only
if /I "%~1"=="--no-audio" goto :opt_no_audio
if /I "%~1"=="--skip-audio-updates" goto :opt_no_audio
if /I "%~1"=="--exact" goto :opt_exact
if /I "%~1"=="--hash-asset-updates" goto :opt_exact

rem First build of the feed.
if /I "%~1"=="--first-time" goto :opt_first_time
if /I "%~1"=="--init-build" goto :opt_first_time
if /I "%~1"=="--baseline-only" goto :opt_first_time

rem Long-form folder flags, kept for scripts and for one-off overrides.
if /I "%~1"=="--previous-export-root" goto :opt_old_root
if /I "%~1"=="--old-export-root" goto :opt_old_root
if /I "%~1"=="--export-root" goto :opt_new_root

rem Old-folder cleanup.
if /I "%~1"=="--prune-old" goto :opt_prune_old
if /I "%~1"=="--prune-previous-export-untracked" goto :opt_prune_old
if /I "%~1"=="--dry-run" goto :opt_dry_run
if /I "%~1"=="--dry-run-prune-previous-export-untracked" goto :opt_prune_dry_run

rem Accepted and ignored: assets and audio are compared by default.
if /I "%~1"=="--include-asset-updates" goto :next_option
if /I "%~1"=="--include-audio-updates" goto :next_option

rem Anything else, including its value, goes to scripts\build_updates.py.
set "EXTRA_ARGS=%EXTRA_ARGS% "%~1""
shift
goto :parse_options

:opt_text_only
set "MODE_ARGS=%MODE_ARGS% --skip-asset-updates"
shift
goto :parse_options

:opt_no_audio
set "MODE_ARGS=%MODE_ARGS% --skip-audio-updates"
shift
goto :parse_options

:opt_exact
set "MODE_ARGS=%MODE_ARGS% --hash-asset-updates"
shift
goto :parse_options

:opt_first_time
set "MODE_ARGS=%MODE_ARGS% --baseline-only"
shift
goto :parse_options

:opt_old_root
if "%~2"=="" goto :missing_value
set "OLD_EXPORT=%~2"
set "ROOTS_GIVEN=1"
shift
shift
goto :parse_options

:opt_new_root
if "%~2"=="" goto :missing_value
set "NEW_EXPORT=%~2"
shift
shift
goto :parse_options

:opt_prune_old
set "PRUNE_OLD=1"
shift
goto :parse_options

:opt_dry_run
set "DRY_RUN=1"
shift
goto :parse_options

:opt_prune_dry_run
set "PRUNE_OLD=1"
set "DRY_RUN=1"
shift
goto :parse_options

:next_option
shift
goto :parse_options

:compose
if "%DRY_RUN%"=="1" if "%PRUNE_OLD%"=="0" (
  echo --dry-run only describes what --prune-old would delete; pass both together.
  exit /b 2
)
if "%PRUNE_OLD%"=="1" if "%DRY_RUN%"=="1" set "MODE_ARGS=%MODE_ARGS% --dry-run-prune-previous-export-untracked"
if "%PRUNE_OLD%"=="1" if "%DRY_RUN%"=="0" set "MODE_ARGS=%MODE_ARGS% --prune-previous-export-untracked"

rem Unnamed sides fall back to endfield_paths.bat.
if not defined OLD_EXPORT if defined ENDFIELD_PREVIOUS_EXPORT_ROOT set "OLD_EXPORT=%ENDFIELD_PREVIOUS_EXPORT_ROOT%"
if not defined NEW_EXPORT if defined ENDFIELD_EXPORT_ROOT set "NEW_EXPORT=%ENDFIELD_EXPORT_ROOT%"
if defined OLD_EXPORT set "ROOT_ARGS=%ROOT_ARGS% --previous-export-root "%OLD_EXPORT%""
if defined NEW_EXPORT set "ROOT_ARGS=%ROOT_ARGS% --export-root "%NEW_EXPORT%""

rem Naming a different old folder invalidates its cached scan, so rebuild that
rem baseline here instead of making the user remember to ask for it.
if "%ROOTS_GIVEN%"=="1" set "ROOT_ARGS=%ROOT_ARGS% --refresh-previous-export-baseline"

if defined ENDFIELD_GAME_ROOT set "ROOT_ARGS=%ROOT_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""

if not defined OLD_EXPORT set "OLD_EXPORT=(scripts\build_updates.py default)"
if not defined NEW_EXPORT set "NEW_EXPORT=(scripts\build_updates.py default)"
echo [build_updates] old: %OLD_EXPORT%
echo [build_updates] new: %NEW_EXPORT%

rem Updates pipeline:
rem - compare WebUI-facing text JSON in the two exports
rem - compare exported image/model/video/audio assets by default
rem - write webui\data\updates\latest.json for the Updates tab
python .\scripts\build_updates.py%ROOT_ARGS%%MODE_ARGS%%EXTRA_ARGS%
if errorlevel 1 exit /b %errorlevel%

endlocal
exit /b 0

:need_two_folders
echo Name both folders, old first: build_updates.bat OLD NEW
echo Or pass neither and let endfield_paths.bat supply them.
exit /b 2

:missing_value
echo Missing folder for %~1.
exit /b 2

:is_help
if /I "%~1"=="--help" exit /b 0
if /I "%~1"=="-h" exit /b 0
if /I "%~1"=="/?" exit /b 0
if /I "%~1"=="/h" exit /b 0
if /I "%~1"=="help" exit /b 0
exit /b 1

:is_option
set "TOKEN=%~1"
if not defined TOKEN exit /b 0
if "%TOKEN:~0,1%"=="-" exit /b 0
if "%TOKEN:~0,1%"=="/" exit /b 0
exit /b 1

:help
if not defined ENDFIELD_PREVIOUS_EXPORT_ROOT set "ENDFIELD_PREVIOUS_EXPORT_ROOT=(unset in endfield_paths.bat)"
if not defined ENDFIELD_EXPORT_ROOT set "ENDFIELD_EXPORT_ROOT=(unset in endfield_paths.bat)"
echo Usage: build_updates.bat [OLD NEW] [options]
echo.
echo Compares two exported game-data folders and builds the WebUI Updates tab.
echo OLD is the export saved from the older game version, NEW is the current
echo export. With no folders it uses the ones set in endfield_paths.bat:
echo.
echo   old: %ENDFIELD_PREVIOUS_EXPORT_ROOT%
echo   new: %ENDFIELD_EXPORT_ROOT%
echo.
echo What gets compared:
echo   The text/JSON that the WebUI displays (Table, MissionRuntimeAsset,
echo   LevelData and friends) is always compared, by content. No option
echo   below changes that part.
echo   On top of it, two media groups are compared by default:
echo     images/models/video   from the asset export roots
echo     decoded audio         from structured\Audio (.flac .wav .wem)
echo.
echo Options:
echo   --first-time   Record NEW as the starting point and report no changes.
echo                  Use this for the very first Updates build.
echo   --text-only    Drop both media groups and compare text only. Fastest,
echo                  because no media folder is walked at all.
echo   --no-audio     Keep images/models/video, drop decoded audio. Audio is
echo                  usually most of the exported files, so this saves most
echo                  of the time and still reports visual assets.
echo   --exact        Compare asset contents by hash instead of by file size.
echo                  This adds no files to the comparison; it decides whether
echo                  an edit that kept the same byte size is noticed at all.
echo                  Without it such an edit reads as unchanged. Assets only,
echo                  because text is already compared by content.
echo   --prune-old    After a successful comparison, delete files in OLD that
echo                  are byte-identical in NEW. Add --dry-run to list them
echo                  without deleting anything.
echo   --help         This text.
echo.
echo Scope and precision are separate dials, so they combine:
echo.
echo   --text-only           text                                  -
echo   (default)             text + images/models/video + audio    sizes
echo   --no-audio            text + images/models/video            sizes
echo   --no-audio --exact    text + images/models/video            hashes
echo   --exact               text + images/models/video + audio    hashes
echo.
echo   --text-only --exact does nothing extra: no assets are fingerprinted.
echo   --text-only --no-audio is redundant: audio is already excluded.
echo   --exact hashes both folders on its first run, then reuses stored
echo   digests while a file keeps its size and timestamp. Alternating
echo   between --exact and the default throws that reuse away.
echo.
echo Examples:
echo   build_updates.bat
echo   build_updates.bat --first-time
echo   build_updates.bat --no-audio
echo   build_updates.bat "D:\exports\Endfield_old" "D:\exports\Endfield_new"
echo.
echo Writes:
echo   webui\data\updates\latest.json
echo   reports\updates\game-data-change-summary.json and .md
echo.
echo Notes:
echo   Naming OLD and NEW rebuilds the cached scan of OLD automatically.
echo   For repeated runs, edit endfield_paths.bat instead of passing folders.
echo   build_updates_by_patch.bat is the other workflow: it detects a game
echo   patch in the installed files, produces the new export, and then calls
echo   this script for you.
echo   Advanced options are passed through to scripts\build_updates.py.
echo   Run "python scripts\build_updates.py --help" to see them.
echo.
endlocal
exit /b 0
