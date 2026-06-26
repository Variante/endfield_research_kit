@echo off
setlocal

set "EXPORT_ARGS="
set "AUDIO_ARGS="
set "EXPORT_FROM_GAME=0"
set "ASSET_MODE=full"

if exist "%~dp0endfield_paths.bat" call "%~dp0endfield_paths.bat"
if errorlevel 1 exit /b %errorlevel%
if defined ENDFIELD_GAME_ROOT set "EXPORT_ARGS=%EXPORT_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_GAME_ROOT set "AUDIO_ARGS=%AUDIO_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_EXPORT_ROOT set "AUDIO_ARGS=%AUDIO_ARGS% --export-root "%ENDFIELD_EXPORT_ROOT%""

:parse_args
if "%~1"=="" goto :parsed_args
if /I "%~1"=="--help" goto :help
if /I "%~1"=="--full-assets" (
  set "ASSET_MODE=full"
  shift
  goto :parse_args
)
if /I "%~1"=="--webui-assets" (
  set "ASSET_MODE=webui"
  shift
  goto :parse_args
)
if /I "%~1"=="--debug-assets" (
  set "ASSET_MODE=debug"
  shift
  goto :parse_args
)
if /I "%~1"=="--animestudio-asset-mode" (
  if "%~2"=="" (
    echo Missing value for --animestudio-asset-mode.
    exit /b 2
  )
  set "ASSET_MODE=%~2"
  shift
  shift
  goto :parse_args
)
if /I "%~1"=="--export-from-game" (
  set "EXPORT_FROM_GAME=1"
  shift
  goto :parse_args
)
if /I "%~1"=="--game-root" (
  if "%~2"=="" (
    echo Missing value for --game-root.
    exit /b 2
  )
  set "EXPORT_ARGS=%EXPORT_ARGS% "%~1" "%~2""
  set "AUDIO_ARGS=%AUDIO_ARGS% "%~1" "%~2""
  shift
  shift
  goto :parse_args
)
set "EXPORT_ARGS=%EXPORT_ARGS% "%~1""
shift
goto :parse_args

:parsed_args
call :validate_asset_mode "%ASSET_MODE%"
if errorlevel 1 exit /b 2

rem Asset export/build pipeline:
rem - rebuild indexes from existing decoded assets by default
rem - export from the installed game only when explicitly requested
rem - skip structured story data and AnimeStudio by default
rem - build selected asset indexes and compact story media lookup
rem - rebuild/link CN audio, decoding first only for --export-from-game
if "%EXPORT_FROM_GAME%"=="0" goto :skip_export_full
python .\scripts\export_full_from_game.py --skip-structured --animestudio-scope assets --animestudio-asset-mode "%ASSET_MODE%" --animestudio-stages maps convert_by_type json_by_type %EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :after_export_full

:skip_export_full
echo [export_assets.bat] Reusing existing decoded assets; pass --export-from-game to refresh from installed game data.

:after_export_full

set "BUILD_ASSET_MODE=%ASSET_MODE%"
if /I "%ASSET_MODE%"=="debug" set "BUILD_ASSET_MODE=full"
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

:validate_asset_mode
if /I "%~1"=="webui" exit /b 0
if /I "%~1"=="full" exit /b 0
if /I "%~1"=="debug" exit /b 0
echo Invalid asset mode: "%~1"
echo Expected webui, full, or debug.
exit /b 2

:help
echo Usage: export_assets.bat [--export-from-game] [--game-root PATH] [export_full_from_game.py options]
echo.
echo Rebuilds WebUI asset indexes plus the compact Story media lookup,
echo then relinks decoded CN Story audio. AnimeStudio full
echo WebUI-facing image/model decode is the default for installed-game refreshes.
echo Story/reference data is handled by export.bat. When Story and assets both
echo need an installed-game refresh, use export.bat --export-from-game --with-assets
echo to run one combined AnimeStudio Story+asset export.
echo.
echo   --export-from-game    Run AnimeStudio asset conversion and CN audio decode.
echo                         Defaults to full WebUI-facing image/model export.
echo   --full-assets         Use the default WebUI-facing image/model export and
echo                         full Assets browser index.
echo   --webui-assets        Use lean WebUI-focused Texture2D media mode.
echo   --debug-assets        Export exhaustive AnimeStudio conversion/JSON diagnostics,
echo                         then build the full Assets browser index.
echo   --game-root PATH      Installed Endfield_Data directory used when
echo                         --export-from-game refreshes decoded assets/audio,
echo                         and for audio linking.
echo   --animestudio-asset-mode webui^|full^|debug
echo                         Lower-level equivalent of --webui-assets/--full-assets/--debug-assets.
echo   --animestudio-jobs N  Passed through when --export-from-game is present.
echo                         Default is 4 for parallel shard/type export.
echo                         Lower this value if peak AnimeStudio memory is too high.
echo   --animestudio-shards N
echo                         Passed through when --export-from-game is present.
echo                         Default is 16 shards with 4 concurrent workers.
echo   --animestudio-type-job-mode auto^|parallel^|merged
echo                         Controls non-sharded AnimeStudio type jobs.
echo                         auto merges JSON type jobs and keeps asset conversion sharded.
echo   --animestudio-stage-merge-mode auto^|never^|aggressive
echo                         Controls guarded Convert+JSON same-process orchestration.
echo                         aggressive requires CLI secondary-export flag support.
echo   --animestudio-dummy-dlls PATH
echo                         DummyDll directory for AnimeStudio MonoBehaviour schema recovery.
echo                         Can also be set with ANIMESTUDIO_DUMMY_DLLS.
echo.
echo If Endfield is installed somewhere else, pass --game-root.
echo For repeated runs, edit endfield_paths.bat instead.
echo Example:
echo   export_assets.bat --export-from-game --game-root "E:\Games\Endfield Game\Endfield_Data"
echo.
echo Other arguments are passed to scripts\export_full_from_game.py when
echo --export-from-game is present. The wrapper also forwards --game-root to
echo the audio builder.
echo.
endlocal
exit /b 0
