@echo off
setlocal

set "EXPORT_ARGS="
set "AUDIO_ARGS="
set "EXPORT_FROM_GAME=0"
set "WITH_ASSETS=0"
set "ASSET_MODE=full"

if exist "%~dp0endfield_paths.bat" call "%~dp0endfield_paths.bat"
if errorlevel 1 exit /b %errorlevel%
if defined ENDFIELD_GAME_ROOT set "EXPORT_ARGS=%EXPORT_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_GAME_ROOT set "AUDIO_ARGS=%AUDIO_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_EXPORT_ROOT set "AUDIO_ARGS=%AUDIO_ARGS% --export-root "%ENDFIELD_EXPORT_ROOT%""

if not defined ENDFIELD_EXPORT_BENCHMARK_ACTIVE (
  if /I not "%~1"=="--help" (
    set "ENDFIELD_EXPORT_BENCHMARK_ACTIVE=1"
    python .\scripts\benchmark_export.py --label export -- "%~f0" %*
    exit /b %errorlevel%
  )
)

:parse_args
if "%~1"=="" goto :parsed_args
if /I "%~1"=="--help" goto :help
if /I "%~1"=="--export-from-game" (
  set "EXPORT_FROM_GAME=1"
  shift
  goto :parse_args
)
if /I "%~1"=="--with-assets" (
  set "WITH_ASSETS=1"
  shift
  goto :parse_args
)
if /I "%~1"=="--full-assets" (
  set "WITH_ASSETS=1"
  set "ASSET_MODE=full"
  shift
  goto :parse_args
)
if /I "%~1"=="--webui-assets" (
  set "WITH_ASSETS=1"
  set "ASSET_MODE=webui"
  shift
  goto :parse_args
)
if /I "%~1"=="--debug-assets" (
  set "WITH_ASSETS=1"
  set "ASSET_MODE=debug"
  shift
  goto :parse_args
)
if /I "%~1"=="--animestudio-asset-mode" (
  if "%~2"=="" (
    echo Missing value for --animestudio-asset-mode.
    exit /b 2
  )
  set "WITH_ASSETS=1"
  set "ASSET_MODE=%~2"
  shift
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

rem WebUI export/build pipeline:
rem - rebuild from existing export_full by default
rem - export from the installed game only when explicitly requested
rem - skip raw_vfs, source inventory, structured data, and AnimeStudio by default
rem - build only CN story/reference data by default
rem - preserve OCR-managed Story sort order under webui\overrides
rem - optionally rebuild Assets tab indexes and relink/decode CN audio with --with-assets
rem - when --export-from-game and --with-assets are combined, run one AnimeStudio scope for Story and assets
if "%EXPORT_FROM_GAME%"=="0" goto :skip_export_full
if "%WITH_ASSETS%"=="1" goto :export_full_with_assets
python .\scripts\export_full_from_game.py --animestudio-scope story --animestudio-stages maps json_by_type %EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :after_export_full

:export_full_with_assets
python .\scripts\export_full_from_game.py --animestudio-scope all --animestudio-asset-mode "%ASSET_MODE%" --animestudio-stages maps convert_by_type json_by_type %EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :after_export_full

:skip_export_full
if "%WITH_ASSETS%"=="1" (
  echo [export.bat] Reusing existing export_full and decoded assets; pass --export-from-game to refresh from installed game data.
) else (
  echo [export.bat] Reusing existing export_full; pass --export-from-game to refresh from installed game data.
)

:after_export_full

python .\scripts\story_builder\refresh_evidence.py
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\build.py --languages CN --default-language CN --skip-audio-link
if errorlevel 1 exit /b %errorlevel%

python .\scripts\build_gameplay_data.py --languages CN --default-language CN
if errorlevel 1 exit /b %errorlevel%

if "%WITH_ASSETS%"=="0" goto :done

set "BUILD_ASSET_MODE=%ASSET_MODE%"
if /I "%ASSET_MODE%"=="debug" set "BUILD_ASSET_MODE=full"
python .\scripts\build_assets.py --mode "%BUILD_ASSET_MODE%"
if errorlevel 1 exit /b %errorlevel%

if "%EXPORT_FROM_GAME%"=="1" goto :decode_audio
python .\scripts\build_audio.py --skip-decode %AUDIO_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :done

:decode_audio
python .\scripts\build_audio.py %AUDIO_ARGS%
if errorlevel 1 exit /b %errorlevel%

:done
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
echo Usage: export.bat [--export-from-game] [--with-assets] [--game-root PATH] [export_full_from_game.py options]
echo.
echo Runs the Story/Reference WebUI refresh from existing export_full by default,
echo rebuilds source-link evidence, builds CN Story/Text/Gameplay data,
echo and preserves OCR-managed Story sort order. Use --with-assets to also
echo rebuild Assets tab data and relink CN audio in the same command.
echo Reading installed game data and tool-based extraction are opt-in.
echo.
echo   --export-from-game    Refresh export_full from installed game data.
echo   --with-assets         Also rebuild asset indexes and relink/decode CN audio.
echo                         With --export-from-game, this uses one combined
echo                         AnimeStudio Story+asset export instead of running
echo                         export.bat and export_assets.bat separately.
echo   --full-assets         With --with-assets, use the default WebUI-facing
echo                         image/model export and full Assets browser index.
echo   --webui-assets        With --with-assets, use lean WebUI-focused Texture2D media mode.
echo   --debug-assets        With --with-assets, export exhaustive AnimeStudio diagnostics,
echo                         then build the full Assets browser index.
echo   --game-root PATH      Installed Endfield_Data directory used for export
echo                         and audio linking.
echo   --animestudio-asset-mode webui^|full^|debug
echo                         Lower-level equivalent of --webui-assets/--full-assets/--debug-assets.
echo   --animestudio-jobs N  Passed through when --export-from-game is present.
echo                         Default is 8 shared workers for pooled AnimeStudio calls.
echo                         Lower this value if peak AnimeStudio memory is too high.
echo   --animestudio-shards N
echo                         Passed through for combined asset exports.
echo                         Default is 16 shards consumed by the shared worker pool.
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
echo Examples:
echo   export.bat --export-from-game --game-root "E:\Games\Endfield Game\Endfield_Data"
echo   export.bat --export-from-game --with-assets --webui-assets
echo.
echo Other arguments are passed to scripts\export_full_from_game.py only when
echo --export-from-game is present. The wrapper also forwards --game-root to
echo the audio linker.
echo Every export.bat run writes a benchmark report under reports\export_benchmarks
echo and updates reports\export_benchmark_latest.md/json.
echo.
echo Companion wrappers:
echo   build_updates.bat     Build the Updates tab feed.
echo   export_assets.bat     Asset/audio-only path; use this when Story is already current.
echo   pack_webui.bat        Create split shareable WebUI zips.
echo.
endlocal
exit /b 0
