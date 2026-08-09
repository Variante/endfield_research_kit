@echo off
setlocal

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

if exist "%~dp0endfield_paths.bat" call "%~dp0endfield_paths.bat"
if errorlevel 1 exit /b %errorlevel%
if defined ENDFIELD_GAME_ROOT set "EXPORT_ARGS=%EXPORT_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_GAME_ROOT set "AUDIO_ARGS=%AUDIO_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_GAME_ROOT set "FRESHNESS_ARGS=--game-root "%ENDFIELD_GAME_ROOT%""
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
if /I "%~1"=="--animestudio-object-index" (
  set "ANIMESTUDIO_OBJECT_INDEX=1"
  set "EXPORT_ARGS=%EXPORT_ARGS% "%~1""
  shift
  goto :parse_args
)
if /I "%~1"=="--full-source-graph" (
  set "FULL_SOURCE_GRAPH=1"
  shift
  goto :parse_args
)
if /I "%~1"=="--mission-pipeline-only" (
  set "MISSION_PIPELINE_ONLY=1"
  shift
  goto :parse_args
)
if /I "%~1"=="--mission-pipeline-data-only" (
  set "MISSION_PIPELINE_DATA_ONLY=1"
  shift
  goto :parse_args
)
if /I "%~1"=="--reuse-timeline-orders" (
  set "REUSE_TIMELINE_ORDERS=1"
  set "STORY_BUILD_ARGS=%STORY_BUILD_ARGS% --timeline-recovery never"
  shift
  goto :parse_args
)
if /I "%~1"=="--reuse-reference" (
  set "REUSE_REFERENCE=1"
  set "STORY_BUILD_ARGS=%STORY_BUILD_ARGS% --reuse-reference"
  shift
  goto :parse_args
)
if /I "%~1"=="--focused-assets" (
  set "WITH_ASSETS=1"
  set "ASSET_MODE=focused"
  shift
  goto :parse_args
)
if /I "%~1"=="--default-assets" (
  set "WITH_ASSETS=1"
  set "ASSET_MODE=default"
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
  set "FRESHNESS_ARGS=--game-root "%~2""
  set "ENDFIELD_GAME_ROOT=%~2"
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
if "%MISSION_PIPELINE_ONLY%"=="1" if "%WITH_ASSETS%"=="1" (
  echo --mission-pipeline-only cannot be combined with --with-assets.
  exit /b 2
)
if "%MISSION_PIPELINE_DATA_ONLY%"=="1" if "%EXPORT_FROM_GAME%"=="1" (
  echo --mission-pipeline-data-only reuses generated Story data and cannot be combined with --export-from-game.
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
  echo --reuse-timeline-orders cannot be combined with --export-from-game because refreshed game data may change Timeline order.
  exit /b 2
)
if "%REUSE_TIMELINE_ORDERS%"=="1" if "%MISSION_PIPELINE_DATA_ONLY%"=="1" (
  echo --mission-pipeline-data-only already skips the Story build; omit --reuse-timeline-orders.
  exit /b 2
)
if "%REUSE_REFERENCE%"=="1" if "%EXPORT_FROM_GAME%"=="1" (
  echo --reuse-reference cannot be combined with --export-from-game because refreshed Table inputs may change Text Tables.
  exit /b 2
)
if "%REUSE_REFERENCE%"=="1" if "%MISSION_PIPELINE_DATA_ONLY%"=="1" (
  echo --mission-pipeline-data-only already skips the Story build; omit --reuse-reference.
  exit /b 2
)
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

python .\scripts\verify_export_freshness.py %FRESHNESS_ARGS%
if errorlevel 1 exit /b %errorlevel%

if "%ANIMESTUDIO_OBJECT_INDEX%"=="1" (
  python .\scripts\story_recovery\build_animestudio_story_guide_consumer_audit.py
  if errorlevel 1 exit /b %errorlevel%
)

python .\scripts\story_builder\refresh_evidence.py
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\build.py --languages CN --default-language CN --skip-audio-link %STORY_BUILD_ARGS%
if errorlevel 1 exit /b %errorlevel%

python .\scripts\build_character_data.py --languages CN --default-language CN
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_recovery\build_protocol_registry_audit.py --ensure-current
if errorlevel 1 exit /b %errorlevel%

python .\scripts\build_mission_pipeline_data.py --refresh-source-story-gap-queue
if errorlevel 1 exit /b %errorlevel%
if "%MISSION_PIPELINE_ONLY%"=="1" (
  echo [export.bat] Mission Pipeline refresh complete; skipped unrelated semantic views and source graph.
  goto :done
)

python .\scripts\build_gameplay_data.py --languages CN --default-language CN
if errorlevel 1 exit /b %errorlevel%

python .\scripts\build_gameplay_asset_refs.py --language CN
if errorlevel 1 exit /b %errorlevel%

python .\scripts\build_projectile_data.py
if errorlevel 1 exit /b %errorlevel%

python .\scripts\build_economy_data.py --languages CN --default-language CN
if errorlevel 1 exit /b %errorlevel%

python .\scripts\build_world_data.py --languages CN --default-language CN
if errorlevel 1 exit /b %errorlevel%

if "%WITH_ASSETS%"=="0" goto :build_semantic_graph

set "BUILD_ASSET_MODE=%ASSET_MODE%"
if /I "%ASSET_MODE%"=="debug" set "BUILD_ASSET_MODE=default"
python .\scripts\build_assets.py --mode "%BUILD_ASSET_MODE%"
if errorlevel 1 exit /b %errorlevel%

if "%EXPORT_FROM_GAME%"=="1" goto :decode_audio
python .\scripts\build_audio.py --skip-decode %AUDIO_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :build_semantic_graph

:decode_audio
python .\scripts\build_audio.py %AUDIO_ARGS%
if errorlevel 1 exit /b %errorlevel%

:build_semantic_graph
if "%FULL_SOURCE_GRAPH%"=="1" goto :build_full_source_graph
echo [export.bat] Building WebUI source graph with relevant original AssetMap rows only.
python .\tools\endfield_source_graph.py build --language CN --relevant-asset-maps --skip-reference-rows --skip-followups
if errorlevel 1 exit /b %errorlevel%
goto :after_source_graph

:build_full_source_graph
echo [export.bat] Building exhaustive investigative source graph.
python .\tools\endfield_source_graph.py build --language CN
if errorlevel 1 exit /b %errorlevel%

:after_source_graph

python .\scripts\build_presentation_data.py --languages CN
if errorlevel 1 exit /b %errorlevel%

python .\scripts\build_combat_relationships.py --languages CN
if errorlevel 1 exit /b %errorlevel%

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

:validate_asset_mode
if /I "%~1"=="focused" exit /b 0
if /I "%~1"=="default" exit /b 0
if /I "%~1"=="debug" exit /b 0
echo Invalid asset mode: "%~1"
echo Expected focused, default, or debug.
exit /b 2

:help
echo Usage: export.bat [--export-from-game] [--with-assets] [--mission-pipeline-only] [--mission-pipeline-data-only] [--reuse-timeline-orders] [--reuse-reference] [--full-source-graph] [--animestudio-object-index] [--game-root PATH] [export_full_from_game.py options]
echo.
echo Runs the Story/Reference WebUI refresh from existing export_full by default,
echo rebuilds source-link evidence, builds CN Story/Text/Gameplay plus the experimental mission pipeline,
echo Projectile/Factory/World data, refreshes the local source graph, then
echo builds Presentation and Combat from fresh graph and AnimeStudio evidence,
echo and preserves OCR-managed Story sort order. Use --with-assets to also
echo rebuild Assets tab data and relink CN audio in the same command.
echo Reading installed game data and tool-based extraction are opt-in.
echo.
echo   --export-from-game    Refresh export_full from installed game data.
echo   --with-assets         Also rebuild asset indexes and relink/decode CN audio.
echo                         With --export-from-game, this uses one combined
echo                         AnimeStudio Story+asset export instead of running
echo                         export.bat and export_assets.bat separately.
echo   --full-source-graph   Index every original Unity AssetMap row and emit
echo                         investigative follow-up reports. The default keeps
echo                         only exact material/shader/texture/FMV map rows needed
echo                         by WebUI views and omits duplicate reference rows.
echo   --mission-pipeline-only
echo                         Refresh original Story evidence, CN Story data, and
echo                         Mission Pipeline data, then stop before unrelated
echo                         Gameplay/Factory/World/graph views.
echo   --mission-pipeline-data-only
echo                         Rebuild Mission Pipeline JSON from the current generated
echo                         Story bundles. Use for pipeline builder or frontend work;
echo                         it verifies export freshness, then skips evidence, Story,
echo                         semantic-view, and source-graph stages.
echo   --reuse-timeline-orders
echo                         Reuse the current binary-derived Timeline line-order index
echo                         during a Story rebuild. Use only when export_full and the
echo                         recovered Timeline inputs have not changed. Incompatible
echo                         with --export-from-game and unnecessary for data-only builds.
echo   --reuse-reference     Validate and preserve the current localized Text Tables
echo                         reference bundle during a Story rebuild. Use only when
echo                         exported Table inputs have not changed. Incompatible with
echo                         --export-from-game and unnecessary for data-only builds.
echo   --focused-assets      With --with-assets, use focused Texture2D media mode.
echo   --default-assets      With --with-assets, use the default WebUI-facing
echo                         image/model export and complete Assets browser index.
echo   --debug-assets        With --with-assets, export exhaustive AnimeStudio diagnostics,
echo                         then build the complete Assets browser index.
echo   --game-root PATH      Installed Endfield_Data directory used for export
echo                         and audio linking.
echo   --animestudio-asset-mode focused^|default^|debug
echo                         Lower-level equivalent of --focused-assets/--default-assets/--debug-assets.
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
echo   --animestudio-object-index
echo                         Build the current AnimeStudio object index during an
echo                         installed-game export, then refresh exact guide-runtime
echo                         non-mission Story consumer evidence before Story builders.
echo   --world-scene-chunk MAP:X:Z
echo                         Export one static world-streaming cell, including InitChunkData
echo                         and StreamingChunkData. May be repeated. Chunk X/Z are
echo                         floor(world X/128) and floor(world Z/128).
echo.
echo If Endfield is installed somewhere else, pass --game-root.
echo For repeated runs, edit endfield_paths.bat instead.
echo Examples:
echo   export.bat --export-from-game --game-root "E:\Games\Endfield Game\Endfield_Data"
echo   export.bat --export-from-game --with-assets --focused-assets
echo   export.bat --export-from-game --world-scene-chunk map02:2:-13
echo   export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
echo.
echo Other arguments are passed to scripts\export_full_from_game.py only when
echo --export-from-game is present. The wrapper also forwards --game-root to
echo the audio linker.
echo Every export.bat run writes a benchmark report under reports\export\benchmarks
echo and updates reports\export\export_benchmark_latest.md/json.
echo.
echo Companion wrappers:
echo   build_updates.bat     Build the Updates tab feed.
echo   export_assets.bat     Asset/audio-only path; use this when Story is already current.
echo   pack_webui.bat        Create split shareable WebUI zips.
echo.
endlocal
exit /b 0
