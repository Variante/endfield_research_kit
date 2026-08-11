@echo off
setlocal

rem Rebuilds the Assets tab and CN Story audio links, leaving Story data alone.
rem
rem   export_assets.bat              reuse the decoded assets already on disk
rem   export_assets.bat --from-game  decode assets and CN audio from the game
rem   export_assets.bat --help       all options

set "EXPORT_ARGS="
set "AUDIO_ARGS="
set "EXPORT_FROM_GAME=0"
set "ASSET_MODE=default"
set "FIRST_PASSTHROUGH="

if exist "%~dp0endfield_paths.bat" call "%~dp0endfield_paths.bat"
if errorlevel 1 exit /b %errorlevel%
if defined ENDFIELD_GAME_ROOT set "EXPORT_ARGS=%EXPORT_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_GAME_ROOT set "AUDIO_ARGS=%AUDIO_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_EXPORT_ROOT set "AUDIO_ARGS=%AUDIO_ARGS% --export-root "%ENDFIELD_EXPORT_ROOT%""

:parse_args
if "%~1"=="" goto :parsed_args
call :is_help "%~1"
if not errorlevel 1 goto :help

rem Where the assets come from.
if /I "%~1"=="--from-game" goto :opt_from_game
if /I "%~1"=="--export-from-game" goto :opt_from_game
if /I "%~1"=="--game-root" goto :opt_game_root

rem Asset scope, named the same way as export.bat.
if /I "%~1"=="--focused-assets" goto :assets_focused
if /I "%~1"=="--default-assets" goto :assets_default
if /I "%~1"=="--debug-assets" goto :assets_debug
if /I "%~1"=="--animestudio-asset-mode" goto :assets_explicit

rem Worker limit.
if /I "%~1"=="--asset-jobs" goto :opt_asset_jobs
if /I "%~1"=="--animestudio-jobs" goto :opt_asset_jobs

rem Anything else, including its value, goes to export_full_from_game.py.
if not defined FIRST_PASSTHROUGH set "FIRST_PASSTHROUGH=%~1"
set "EXPORT_ARGS=%EXPORT_ARGS% "%~1""
shift
goto :parse_args

:opt_from_game
set "EXPORT_FROM_GAME=1"
shift
goto :parse_args

:opt_game_root
if "%~2"=="" goto :missing_game_root
set "EXPORT_ARGS=%EXPORT_ARGS% --game-root "%~2""
set "AUDIO_ARGS=%AUDIO_ARGS% --game-root "%~2""
shift
shift
goto :parse_args

:assets_focused
set "ASSET_MODE=focused"
shift
goto :parse_args

:assets_default
set "ASSET_MODE=default"
shift
goto :parse_args

:assets_debug
set "ASSET_MODE=debug"
shift
goto :parse_args

:assets_explicit
if "%~2"=="" goto :missing_asset_mode
set "ASSET_MODE=%~2"
shift
shift
goto :parse_args

:opt_asset_jobs
if "%~2"=="" goto :missing_asset_jobs
set "EXPORT_ARGS=%EXPORT_ARGS% --animestudio-jobs %~2"
if not defined FIRST_PASSTHROUGH set "FIRST_PASSTHROUGH=--asset-jobs"
shift
shift
goto :parse_args

:parsed_args
call :validate_asset_mode "%ASSET_MODE%"
if errorlevel 1 exit /b 2
if "%EXPORT_FROM_GAME%"=="0" if defined FIRST_PASSTHROUGH goto :passthrough_needs_game

rem Asset export/build pipeline:
rem - rebuild indexes from existing decoded assets by default
rem - export from the installed game only when explicitly requested
rem - skip structured story data and AnimeStudio by default
rem - build selected asset indexes and compact story media lookup
rem - rebuild/link CN audio, decoding first only for --from-game
if "%EXPORT_FROM_GAME%"=="0" goto :skip_export_full
python .\scripts\export_full_from_game.py --skip-structured --animestudio-scope assets --animestudio-asset-mode "%ASSET_MODE%" --animestudio-stages maps convert_by_type json_by_type %EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :after_export_full

:skip_export_full
echo [export_assets.bat] Reusing existing decoded assets; pass --from-game to refresh from installed game data.

:after_export_full

set "BUILD_ASSET_MODE=%ASSET_MODE%"
if /I "%ASSET_MODE%"=="debug" set "BUILD_ASSET_MODE=default"
python .\scripts\build_assets.py --mode "%BUILD_ASSET_MODE%"
if errorlevel 1 exit /b %errorlevel%

if "%EXPORT_FROM_GAME%"=="1" goto :decode_audio
python .\scripts\build_audio.py --skip-decode %AUDIO_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :after_audio

:decode_audio
python .\scripts\build_audio.py %AUDIO_ARGS%
if errorlevel 1 exit /b %errorlevel%

:after_audio

endlocal
exit /b 0

:passthrough_needs_game
echo "%FIRST_PASSTHROUGH%" only applies while decoding from the installed game.
echo Add --from-game, or drop that option.
exit /b 2

:missing_game_root
echo Missing folder for --game-root.
exit /b 2

:missing_asset_mode
echo Missing value for --animestudio-asset-mode.
echo Expected focused, default, or debug.
exit /b 2

:missing_asset_jobs
echo Missing value for --asset-jobs. Expected a worker count, for example 8.
exit /b 2

:validate_asset_mode
if /I "%~1"=="focused" exit /b 0
if /I "%~1"=="default" exit /b 0
if /I "%~1"=="debug" exit /b 0
echo Invalid asset mode: "%~1"
echo Expected focused, default, or debug.
exit /b 2

:is_help
if /I "%~1"=="--help" exit /b 0
if /I "%~1"=="-h" exit /b 0
if /I "%~1"=="/?" exit /b 0
if /I "%~1"=="/h" exit /b 0
if /I "%~1"=="help" exit /b 0
exit /b 1

:help
echo Usage: export_assets.bat [options]
echo.
echo Rebuilds the WebUI Assets tab indexes and the compact Story media lookup,
echo then relinks decoded CN Story audio. Story and Text Tables data is
echo export.bat's job, not this script's.
echo.
echo Options:
echo   --from-game        Decode images, models and CN audio from the installed
echo                      game first. Slow. Without it, this script only
echo                      reindexes and relinks what is already decoded.
echo   --focused-assets   Asset scope, narrowest to broadest. The default scope
echo   --default-assets   is --default-assets, which covers the WebUI-facing
echo   --debug-assets     image/model export plus the complete Assets index.
echo                      --debug-assets also writes AnimeStudio diagnostics.
echo   --game-root PATH   Installed Endfield_Data folder. Defaults to the one
echo                      in endfield_paths.bat.
echo   --asset-jobs N     AnimeStudio workers during --from-game. Default 8.
echo                      Lower it if AnimeStudio peak memory is too high.
echo   --help             This text.
echo.
echo Examples:
echo   export_assets.bat
echo   export_assets.bat --from-game
echo   export_assets.bat --from-game --focused-assets
echo   export_assets.bat --from-game --game-root "E:\Games\Endfield Game\Endfield_Data"
echo.
echo Notes:
echo   When Story and assets both need an installed-game refresh, prefer
echo   "export.bat --from-game --with-assets": it runs one combined AnimeStudio
echo   Story+asset export instead of two separate passes.
echo   Static world scene chunks need the structured export, so use
echo   "export.bat --from-game --world-scene-chunk MAP:X:Z" for those.
echo   For repeated runs, edit endfield_paths.bat instead of passing --game-root.
echo   With --from-game, any other option is passed to
echo   scripts\export_full_from_game.py, including the --animestudio-* tuning;
echo   run "python scripts\export_full_from_game.py --help" to see them.
echo   The older --export-from-game, --animestudio-jobs and
echo   --animestudio-asset-mode spellings still work.
echo.
endlocal
exit /b 0
