@echo off
setlocal

rem Rebuilds the WebUI from the export_full folder that is already on disk.
rem
rem   export.bat                     rebuild from the current export_full
rem   export.bat --from-game         re-extract from the installed game first
rem   export.bat --with-assets       also rebuild assets and CN audio
rem   export.bat --help              all options

set "EXPORT_ARGS="
set "AUDIO_ARGS="
set "FRESHNESS_ARGS="
set "STORY_BUILD_ARGS="
set "EXPORT_FROM_GAME=0"
set "WITH_ASSETS=0"
set "ASSET_MODE=default"
set "FULL_SOURCE_GRAPH=0"
set "MISSION_PIPELINE_ONLY=0"
set "MISSION_PIPELINE_DATA_ONLY=0"
set "REUSE_TIMELINE_ORDERS=0"
set "REUSE_REFERENCE=0"
set "ANIMESTUDIO_OBJECT_INDEX=0"
set "WEBUI_JOBS=4"
set "FIRST_PASSTHROUGH="

if exist "%~dp0endfield_paths.bat" call "%~dp0endfield_paths.bat"
if errorlevel 1 exit /b %errorlevel%
if defined ENDFIELD_GAME_ROOT set "EXPORT_ARGS=%EXPORT_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_GAME_ROOT set "AUDIO_ARGS=%AUDIO_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_GAME_ROOT set "FRESHNESS_ARGS=--game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_EXPORT_ROOT set "AUDIO_ARGS=%AUDIO_ARGS% --export-root "%ENDFIELD_EXPORT_ROOT%""

rem Answer any help request before the benchmark wrapper re-runs this script.
for %%A in (%*) do (
  call :is_help "%%~A"
  if not errorlevel 1 goto :help
)

if defined ENDFIELD_EXPORT_BENCHMARK_ACTIVE goto :parse_args
set "ENDFIELD_EXPORT_BENCHMARK_ACTIVE=1"
python .\scripts\benchmark_export.py --label export -- "%~f0" %*
exit /b %errorlevel%

:parse_args
if "%~1"=="" goto :parsed_args

rem Where the data comes from.
if /I "%~1"=="--from-game" goto :opt_from_game
if /I "%~1"=="--export-from-game" goto :opt_from_game
if /I "%~1"=="--game-root" goto :opt_game_root

rem Assets and audio.
if /I "%~1"=="--with-assets" goto :opt_with_assets
if /I "%~1"=="--focused-assets" goto :assets_focused
if /I "%~1"=="--default-assets" goto :assets_default
if /I "%~1"=="--debug-assets" goto :assets_debug
if /I "%~1"=="--animestudio-asset-mode" goto :assets_explicit

rem Faster partial rebuilds.
if /I "%~1"=="--mission-pipeline-only" goto :opt_pipeline_only
if /I "%~1"=="--pipeline-only" goto :opt_pipeline_only
if /I "%~1"=="--mission-pipeline-data-only" goto :opt_pipeline_data_only
if /I "%~1"=="--pipeline-data-only" goto :opt_pipeline_data_only
if /I "%~1"=="--reuse-timeline-orders" goto :opt_reuse_timeline
if /I "%~1"=="--reuse-reference" goto :opt_reuse_reference

rem Tuning.
if /I "%~1"=="--webui-jobs" goto :opt_webui_jobs
if /I "%~1"=="--asset-jobs" goto :opt_asset_jobs
if /I "%~1"=="--animestudio-jobs" goto :opt_asset_jobs
if /I "%~1"=="--full-source-graph" goto :opt_full_source_graph
if /I "%~1"=="--animestudio-object-index" goto :opt_object_index

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
set "FRESHNESS_ARGS=--game-root "%~2""
set "ENDFIELD_GAME_ROOT=%~2"
shift
shift
goto :parse_args

:opt_with_assets
set "WITH_ASSETS=1"
shift
goto :parse_args

:assets_focused
set "WITH_ASSETS=1"
set "ASSET_MODE=focused"
shift
goto :parse_args

:assets_default
set "WITH_ASSETS=1"
set "ASSET_MODE=default"
shift
goto :parse_args

:assets_debug
set "WITH_ASSETS=1"
set "ASSET_MODE=debug"
shift
goto :parse_args

:assets_explicit
if "%~2"=="" goto :missing_asset_mode
set "WITH_ASSETS=1"
set "ASSET_MODE=%~2"
shift
shift
goto :parse_args

:opt_pipeline_only
set "MISSION_PIPELINE_ONLY=1"
shift
goto :parse_args

:opt_pipeline_data_only
set "MISSION_PIPELINE_DATA_ONLY=1"
shift
goto :parse_args

:opt_reuse_timeline
set "REUSE_TIMELINE_ORDERS=1"
set "STORY_BUILD_ARGS=%STORY_BUILD_ARGS% --timeline-recovery never"
shift
goto :parse_args

:opt_reuse_reference
set "REUSE_REFERENCE=1"
set "STORY_BUILD_ARGS=%STORY_BUILD_ARGS% --reuse-reference"
shift
goto :parse_args

:opt_webui_jobs
if "%~2"=="" goto :missing_webui_jobs
set "WEBUI_JOBS=%~2"
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

:opt_full_source_graph
set "FULL_SOURCE_GRAPH=1"
shift
goto :parse_args

:opt_object_index
set "ANIMESTUDIO_OBJECT_INDEX=1"
set "EXPORT_ARGS=%EXPORT_ARGS% --animestudio-object-index"
shift
goto :parse_args

:parsed_args
rem Reject contradictory input before starting any Python process.
call :validate_asset_mode "%ASSET_MODE%"
if errorlevel 1 exit /b 2
if "%EXPORT_FROM_GAME%"=="0" if defined FIRST_PASSTHROUGH goto :passthrough_needs_game
if "%MISSION_PIPELINE_ONLY%"=="1" if "%WITH_ASSETS%"=="1" (
  echo --mission-pipeline-only cannot be combined with --with-assets.
  exit /b 2
)
if "%MISSION_PIPELINE_DATA_ONLY%"=="1" if "%EXPORT_FROM_GAME%"=="1" (
  echo --mission-pipeline-data-only reuses generated Story data and cannot be combined with --from-game.
  exit /b 2
)
if "%MISSION_PIPELINE_DATA_ONLY%"=="1" if "%WITH_ASSETS%"=="1" (
  echo --mission-pipeline-data-only cannot be combined with asset refresh flags.
  exit /b 2
)
if "%MISSION_PIPELINE_DATA_ONLY%"=="1" if "%FULL_SOURCE_GRAPH%"=="1" (
  echo --mission-pipeline-data-only cannot be combined with --full-source-graph.
  exit /b 2
)
if "%MISSION_PIPELINE_DATA_ONLY%"=="1" if "%MISSION_PIPELINE_ONLY%"=="1" (
  echo Choose either --mission-pipeline-only or --mission-pipeline-data-only.
  exit /b 2
)
if "%REUSE_TIMELINE_ORDERS%"=="1" if "%EXPORT_FROM_GAME%"=="1" (
  echo --reuse-timeline-orders cannot be combined with --from-game because refreshed game data may change Timeline order.
  exit /b 2
)
if "%REUSE_TIMELINE_ORDERS%"=="1" if "%MISSION_PIPELINE_DATA_ONLY%"=="1" (
  echo --mission-pipeline-data-only already skips the Story build; omit --reuse-timeline-orders.
  exit /b 2
)
if "%REUSE_REFERENCE%"=="1" if "%EXPORT_FROM_GAME%"=="1" (
  echo --reuse-reference cannot be combined with --from-game because refreshed Table inputs may change Text Tables.
  exit /b 2
)
if "%REUSE_REFERENCE%"=="1" if "%MISSION_PIPELINE_DATA_ONLY%"=="1" (
  echo --mission-pipeline-data-only already skips the Story build; omit --reuse-reference.
  exit /b 2
)
python .\scripts\build_webui_views.py --jobs "%WEBUI_JOBS%" --mission-pipeline-only --dry-run >nul
if errorlevel 1 exit /b 2
if "%MISSION_PIPELINE_DATA_ONLY%"=="1" goto :verify_mission_pipeline_data_only
goto :normal_webui_build

:verify_mission_pipeline_data_only
rem The data-only path is intentionally fast, but it must still report when
rem generated Story inputs no longer match the installed original data.
python .\scripts\verify_export_freshness.py %FRESHNESS_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :build_mission_pipeline_data_only

:normal_webui_build

rem WebUI export/build pipeline:
rem - rebuild from existing export_full by default
rem - export from the installed game only when explicitly requested
rem - skip raw_vfs, source inventory, structured data, and AnimeStudio by default
rem - build only CN story/reference data by default
rem - preserve OCR-managed Story sort order under webui\overrides
rem - optionally rebuild Assets tab indexes and relink/decode CN audio with --with-assets
rem - when --from-game and --with-assets are combined, run one AnimeStudio scope for Story and assets
if "%EXPORT_FROM_GAME%"=="1" if "%WITH_ASSETS%"=="0" python .\scripts\export_full_from_game.py --animestudio-scope story --animestudio-stages maps json_by_type %EXPORT_ARGS%
if "%EXPORT_FROM_GAME%"=="1" if "%WITH_ASSETS%"=="0" if errorlevel 1 exit /b %errorlevel%
if "%EXPORT_FROM_GAME%"=="1" if "%WITH_ASSETS%"=="1" python .\scripts\export_full_from_game.py --animestudio-scope all --animestudio-asset-mode "%ASSET_MODE%" --animestudio-stages maps convert_by_type json_by_type %EXPORT_ARGS%
if "%EXPORT_FROM_GAME%"=="1" if "%WITH_ASSETS%"=="1" if errorlevel 1 exit /b %errorlevel%
if "%EXPORT_FROM_GAME%"=="0" if "%WITH_ASSETS%"=="1" echo [export.bat] Reusing existing export_full and decoded assets; pass --from-game to refresh from installed game data.
if "%EXPORT_FROM_GAME%"=="0" if "%WITH_ASSETS%"=="0" echo [export.bat] Reusing existing export_full; pass --from-game to refresh from installed game data.

python .\scripts\verify_export_freshness.py %FRESHNESS_ARGS%
if errorlevel 1 exit /b %errorlevel%

if "%ANIMESTUDIO_OBJECT_INDEX%"=="0" goto :refresh_evidence
python .\scripts\story_recovery\build_animestudio_story_guide_consumer_audit.py
if errorlevel 1 exit /b %errorlevel%

:refresh_evidence
python .\scripts\story_builder\refresh_evidence.py
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\build.py --languages CN --default-language CN --skip-audio-link %STORY_BUILD_ARGS%
if errorlevel 1 exit /b %errorlevel%

set "WEBUI_VIEW_ARGS=--jobs "%WEBUI_JOBS%" --asset-mode "%ASSET_MODE%""
if "%MISSION_PIPELINE_ONLY%"=="1" set "WEBUI_VIEW_ARGS=%WEBUI_VIEW_ARGS% --mission-pipeline-only"
if "%WITH_ASSETS%"=="1" set "WEBUI_VIEW_ARGS=%WEBUI_VIEW_ARGS% --with-assets"
if "%EXPORT_FROM_GAME%"=="1" if "%WITH_ASSETS%"=="1" set "WEBUI_VIEW_ARGS=%WEBUI_VIEW_ARGS% --decode-audio"
if "%FULL_SOURCE_GRAPH%"=="1" set "WEBUI_VIEW_ARGS=%WEBUI_VIEW_ARGS% --full-source-graph"
python .\scripts\build_webui_views.py %WEBUI_VIEW_ARGS% %AUDIO_ARGS%
if errorlevel 1 exit /b %errorlevel%
if "%MISSION_PIPELINE_ONLY%"=="1" echo [export.bat] Mission Pipeline refresh complete; skipped unrelated semantic views and source graph.

:done
endlocal
exit /b 0

:build_mission_pipeline_data_only
echo [export.bat] Reusing current generated Story bundles and evidence.
python .\scripts\story_recovery\build_protocol_registry_audit.py --ensure-current
if errorlevel 1 exit /b %errorlevel%

python .\scripts\build_mission_pipeline_data.py
if errorlevel 1 exit /b %errorlevel%
echo [export.bat] Mission Pipeline data refresh complete; no Story, evidence, semantic-view, or source-graph rebuild was run.
goto :done

:passthrough_needs_game
echo "%FIRST_PASSTHROUGH%" only applies while re-extracting from the installed game.
echo Add --from-game, or drop that option.
exit /b 2

:missing_game_root
echo Missing folder for --game-root.
exit /b 2

:missing_asset_mode
echo Missing value for --animestudio-asset-mode.
echo Expected focused, default, or debug.
exit /b 2

:missing_webui_jobs
echo Missing value for --webui-jobs. Expected a builder count, for example 4.
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
echo Usage: export.bat [options]
echo.
echo Rebuilds the WebUI from the export_full folder already on disk: CN Story
echo and Text Tables, Mission Pipeline, Gameplay and Projectile data, the
echo source graph, then Combat. It first checks that export_full still matches
echo the installed game. It does not read installed game data unless asked.
echo.
echo Common options:
echo   --from-game        Re-extract export_full from the installed game first.
echo                      Slow; needed after the game updates itself.
echo   --with-assets      Also rebuild the Assets tab and relink/decode CN
echo                      audio. Together with --from-game this runs one
echo                      combined AnimeStudio Story+asset export instead of
echo                      two separate passes.
echo   --focused-assets   Asset scope, narrowest to broadest. Each one implies
echo   --default-assets   --with-assets. The default scope is --default-assets.
echo   --debug-assets     --debug-assets also writes AnimeStudio diagnostics.
echo   --game-root PATH   Installed Endfield_Data folder. Defaults to the one
echo                      in endfield_paths.bat.
echo   --help             This text.
echo.
echo Faster partial rebuilds, for editing work rather than a fresh export:
echo   --mission-pipeline-only
echo                      Story evidence, CN Story and Mission Pipeline, then
echo                      stop before Gameplay, Projectile, graph and Combat.
echo   --mission-pipeline-data-only
echo                      Rebuild only Mission Pipeline JSON from the Story
echo                      bundles already on disk. Checks export freshness,
echo                      then skips every other stage. Use this for pipeline
echo                      builder or frontend work.
echo   --reuse-timeline-orders
echo                      Keep the current Timeline line-order index during a
echo                      Story rebuild. Only correct while export_full and the
echo                      recovered Timeline inputs are unchanged.
echo   --reuse-reference  Keep the current localized Text Tables bundle during
echo                      a Story rebuild. Only correct while the exported
echo                      Tables are unchanged.
echo.
echo Tuning:
echo   --webui-jobs N     Concurrent post-Story builders. Default 4. Dependency
echo                      joins and graph freshness stay serialized regardless.
echo   --asset-jobs N     AnimeStudio workers during --from-game. Default 8.
echo                      Lower it if AnimeStudio peak memory is too high.
echo   --full-source-graph
echo                      Index every original Unity AssetMap row and emit
echo                      follow-up reports. The default keeps only the
echo                      material/shader/texture/FMV rows the WebUI needs.
echo   --animestudio-object-index
echo                      Build the object index during --from-game, then
echo                      refresh guide-runtime Story consumer evidence.
echo.
echo Examples:
echo   export.bat
echo   export.bat --from-game
echo   export.bat --from-game --with-assets --focused-assets
echo   export.bat --from-game --game-root "E:\Games\Endfield Game\Endfield_Data"
echo   export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
echo.
echo Notes:
echo   For repeated runs, edit endfield_paths.bat instead of passing --game-root.
echo   Story sort order in webui\overrides\story_order.json is yours to manage;
echo   export.bat never rewrites it.
echo   Every run writes a wall-time and RAM benchmark under reports\export.
echo   With --from-game, any other option is passed to
echo   scripts\export_full_from_game.py. That is where the --animestudio-*
echo   tuning and --world-scene-chunk MAP:X:Z live; run
echo   "python scripts\export_full_from_game.py --help" to see them.
echo   The older --export-from-game, --animestudio-jobs and
echo   --animestudio-asset-mode spellings still work.
echo.
echo Companion wrappers:
echo   export_assets.bat  Assets and audio only, when Story is already current.
echo   build_updates.bat  Build the Updates tab feed.
echo   pack_webui.bat     Create split shareable WebUI zips.
echo.
endlocal
exit /b 0
