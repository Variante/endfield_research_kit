@echo off
setlocal

rem Rebuilds the WebUI from the export_full folder that is already on disk.
rem
rem   export.bat                     rebuild from the current export_full
rem   export.bat --from-game         re-extract from the installed game first
rem   export.bat --with-assets       also rebuild assets and CN audio
rem   export.bat --assets-only       assets and post-Story views, no Story rebuild
rem   export.bat --help              all options

set "EXPORT_ARGS="
set "GAME_ROOT_ARG="
set "EXPORT_ROOT_ARG="
set "EXTRACTION_OUTPUT_ARG="
set "STORY_BUILD_ARGS="
set "EXPORT_FROM_GAME=0"
set "WITH_ASSETS=0"
set "ASSET_MODE=default"
set "FULL_SOURCE_GRAPH=0"
set "BUILD_SCOPE=full"
set "SCOPE_FLAG="
set "ANIMESTUDIO_OBJECT_INDEX=0"
set "WEBUI_JOBS=4"
set "FIRST_PASSTHROUGH="
set "BENCH_LABEL=export"

if exist "%~dp0endfield_paths.bat" call "%~dp0endfield_paths.bat"
if errorlevel 1 exit /b %errorlevel%
rem One variable per root. Every stage that needs a root appends the same one,
rem so a new stage cannot silently miss it the way a per-stage copy can.
if defined ENDFIELD_GAME_ROOT set "GAME_ROOT_ARG=--game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_EXPORT_ROOT set "EXPORT_ROOT_ARG=--export-root "%ENDFIELD_EXPORT_ROOT%""
if defined ENDFIELD_EXPORT_ROOT set "EXTRACTION_OUTPUT_ARG=--output "%ENDFIELD_EXPORT_ROOT%""

rem Answer any help request, and pick the benchmark label, before the benchmark
rem wrapper re-runs this script.
for %%A in (%*) do (
  call :is_help "%%~A"
  if not errorlevel 1 goto :help
  if /I "%%~A"=="--assets-only" set "BENCH_LABEL=export_assets"
)

if defined ENDFIELD_EXPORT_BENCHMARK_ACTIVE goto :parse_args
set "ENDFIELD_EXPORT_BENCHMARK_ACTIVE=1"
echo [export.bat %time%] Starting monitored export run; benchmark and peak-memory reports will be written under reports\export.
python .\scripts\benchmark_export.py --label %BENCH_LABEL% -- "%~f0" %*
exit /b %errorlevel%

:parse_args
if "%~1"=="" goto :parsed_args

rem Where the data comes from.
if /I "%~1"=="--from-game" goto :opt_from_game
if /I "%~1"=="--game-root" goto :opt_game_root

rem Assets and audio.
if /I "%~1"=="--with-assets" goto :opt_with_assets
if /I "%~1"=="--focused-assets" goto :assets_focused
if /I "%~1"=="--default-assets" goto :assets_default
if /I "%~1"=="--debug-assets" goto :assets_debug

rem Build scope. At most one of these may be given.
if /I "%~1"=="--story-only" goto :opt_story_only
if /I "%~1"=="--assets-only" goto :opt_assets_only

rem Tuning.
if /I "%~1"=="--webui-jobs" goto :opt_webui_jobs
if /I "%~1"=="--asset-jobs" goto :opt_asset_jobs
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
set "GAME_ROOT_ARG=--game-root "%~2""
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

:opt_story_only
call :set_scope story --story-only
if errorlevel 1 exit /b 2
shift
goto :parse_args

:opt_assets_only
call :set_scope assets --assets-only
if errorlevel 1 exit /b 2
set "WITH_ASSETS=1"
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
set "EXPORT_ARGS=%EXPORT_ARGS% --asset-jobs %~2"
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
rem Two derived facts drive the rest of the script, so scope-specific stage
rem checks stay out of the pipeline below.
set "STORY_BUILD=1"
set "POST_STORY_VIEWS=1"
if "%BUILD_SCOPE%"=="story" set "POST_STORY_VIEWS=0"
if "%BUILD_SCOPE%"=="assets" set "STORY_BUILD=0"

rem Reject contradictory input before starting any Python process.
call :validate_asset_mode "%ASSET_MODE%"
if errorlevel 1 exit /b 2
if "%EXPORT_FROM_GAME%"=="0" if defined FIRST_PASSTHROUGH goto :passthrough_needs_game
if "%STORY_BUILD%"=="0" if "%ANIMESTUDIO_OBJECT_INDEX%"=="1" goto :object_index_without_story
if "%BUILD_SCOPE%"=="story" if "%WITH_ASSETS%"=="1" (
  echo --story-only cannot be combined with --with-assets or an asset scope.
  exit /b 2
)
if "%BUILD_SCOPE%"=="story" if "%FULL_SOURCE_GRAPH%"=="1" (
  echo --story-only cannot be combined with --full-source-graph.
  exit /b 2
)
rem Assemble the post-Story view arguments now so the preflight below can check
rem the exact combination this run will use, not a stand-in.
set "WEBUI_VIEW_ARGS=--jobs "%WEBUI_JOBS%" --asset-mode "%ASSET_MODE%""
if "%WITH_ASSETS%"=="1" set "WEBUI_VIEW_ARGS=%WEBUI_VIEW_ARGS% --with-assets"
if "%EXPORT_FROM_GAME%"=="1" if "%WITH_ASSETS%"=="1" set "WEBUI_VIEW_ARGS=%WEBUI_VIEW_ARGS% --decode-audio"
if "%FULL_SOURCE_GRAPH%"=="1" set "WEBUI_VIEW_ARGS=%WEBUI_VIEW_ARGS% --full-source-graph"

call :stage "Resolved export options"
if "%EXPORT_FROM_GAME%"=="1" (echo [export.bat] Source: installed game refresh) else (echo [export.bat] Source: existing export_full)
if "%WITH_ASSETS%"=="1" (echo [export.bat] Assets/audio: enabled, scope %ASSET_MODE%) else (echo [export.bat] Assets/audio: skipped)
if "%BUILD_SCOPE%"=="full" echo [export.bat] Build scope: complete curated WebUI pipeline
if "%BUILD_SCOPE%"=="story" echo [export.bat] Build scope: Story and Text Tables only
if "%BUILD_SCOPE%"=="assets" echo [export.bat] Build scope: assets, audio, and post-Story views; current Story is reused
echo [export.bat] Post-Story worker limit: %WEBUI_JOBS%

python .\scripts\build_webui_views.py %WEBUI_VIEW_ARGS% %GAME_ROOT_ARG% %EXPORT_ROOT_ARG% --dry-run >nul
if errorlevel 1 exit /b 2

rem WebUI export/build pipeline:
rem - rebuild from existing export_full by default
rem - export from the installed game only when explicitly requested
rem - skip raw_vfs, source inventory, structured data, and AnimeStudio by default
rem - build only CN story/reference data by default
rem - preserve OCR-managed Story sort order under webui\overrides
rem - optionally rebuild Assets tab indexes and relink/decode CN audio with --with-assets
rem - when --from-game and --with-assets are combined, run one AnimeStudio scope for Story and assets
if "%EXPORT_FROM_GAME%"=="0" goto :extract_skipped
if "%BUILD_SCOPE%"=="assets" goto :extract_assets
if "%WITH_ASSETS%"=="1" goto :extract_story_and_assets
goto :extract_story

:extract_story
call :stage "Extracting Story and Table inputs from the installed game (AnimeStudio maps and JSON)"
python .\scripts\export_full_from_game.py --animestudio-scope story --animestudio-stages maps json_by_type %GAME_ROOT_ARG% %EXTRACTION_OUTPUT_ARG% %EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :extract_done

:extract_story_and_assets
call :stage "Extracting Story, Tables, assets, and materials in one AnimeStudio pass (scope: %ASSET_MODE%)"
python .\scripts\export_full_from_game.py --animestudio-scope all --asset-mode "%ASSET_MODE%" --animestudio-stages maps convert_by_type json_by_type %GAME_ROOT_ARG% %EXTRACTION_OUTPUT_ARG% %EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :extract_done

:extract_assets
call :stage "Exporting images, models, materials, and audio from the installed game (scope: %ASSET_MODE%)"
python .\scripts\export_full_from_game.py --skip-structured --animestudio-scope assets --asset-mode "%ASSET_MODE%" --animestudio-stages maps convert_by_type json_by_type %GAME_ROOT_ARG% %EXTRACTION_OUTPUT_ARG% %EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :extract_done

:extract_skipped
if "%WITH_ASSETS%"=="1" echo [export.bat] Reusing existing export_full and decoded assets; pass --from-game to refresh from installed game data.
if "%WITH_ASSETS%"=="0" echo [export.bat] Reusing existing export_full; pass --from-game to refresh from installed game data.

:extract_done
rem Every scope gets this check, including the fast ones: a scoped rebuild must
rem still report when its inputs no longer match the installed original data.
call :stage "Checking export_full freshness against the installed game"
python .\scripts\verify_export_freshness.py %GAME_ROOT_ARG%
if errorlevel 1 exit /b %errorlevel%

if "%STORY_BUILD%"=="0" goto :story_reused
if "%ANIMESTUDIO_OBJECT_INDEX%"=="0" goto :refresh_evidence
call :stage "Refreshing AnimeStudio guide-runtime Story consumer evidence"
python -m scripts.story_builder.animestudio_story_guide
if errorlevel 1 exit /b %errorlevel%

:refresh_evidence
call :stage "Refreshing Story recovery evidence and source links"
python -m scripts.story_builder.refresh_evidence
if errorlevel 1 exit /b %errorlevel%

call :stage "Building CN Story conversations, missions, and Text Tables"
python -m scripts.story_builder.build --languages CN --default-language CN %STORY_BUILD_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :story_done

:story_reused
echo [export.bat] Reusing current generated Story bundles and evidence.

:story_done
if "%POST_STORY_VIEWS%"=="0" (
  echo [export.bat] Story-only refresh complete; skipped Mission Pipeline and all post-Story semantic views.
  goto :done
)

if "%BUILD_SCOPE%"=="assets" call :stage "Building Mission Pipeline, map recovery, Characters, Gameplay, projectiles, Assets, CN audio, source graph, and combat relationships"
if "%BUILD_SCOPE%"=="full" if "%WITH_ASSETS%"=="0" call :stage "Building Mission Pipeline, Characters, Gameplay, map recovery, source graph, and graph consumers"
if "%BUILD_SCOPE%"=="full" if "%WITH_ASSETS%"=="1" call :stage "Building semantic views, asset indexes, CN audio, map recovery, source graph, and graph consumers"
python .\scripts\build_webui_views.py %WEBUI_VIEW_ARGS% %GAME_ROOT_ARG% %EXPORT_ROOT_ARG%
if errorlevel 1 exit /b %errorlevel%
if "%BUILD_SCOPE%"=="assets" echo [export.bat] Post-Story semantic, asset, and audio refresh complete; Story was not rebuilt.

:done
call :stage "Export pipeline complete"
endlocal
exit /b 0

:set_scope
if not "%BUILD_SCOPE%"=="full" (
  echo Choose only one build scope; %SCOPE_FLAG% cannot be combined with %~2.
  exit /b 2
)
set "BUILD_SCOPE=%~1"
set "SCOPE_FLAG=%~2"
exit /b 0

:object_index_without_story
echo %SCOPE_FLAG% skips Story evidence, so --animestudio-object-index would not refresh its Story consumer evidence.
echo Use a Story-building scope, or omit --animestudio-object-index.
exit /b 2

:passthrough_needs_game
echo "%FIRST_PASSTHROUGH%" only applies while re-extracting from the installed game.
echo Add --from-game, or drop that option.
exit /b 2

:missing_game_root
echo Missing folder for --game-root.
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

:stage
echo.
echo [export.bat %time%] === %~1 ===
exit /b 0

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
echo Build scope. At most one of these may be given:
echo   --story-only       Build Story and Text Tables, then stop before Mission
echo                      Pipeline and every post-Story semantic view. May be
echo                      combined with --from-game for a lean first export.
echo   --assets-only      Rebuild every post-Story semantic view, the Assets
echo                      indexes and CN audio from the current generated
echo                      Story. Skips Story evidence, Story and Text Tables.
echo                      Implies --with-assets. This is what export_assets.bat
echo                      now runs. With --from-game it preserves structured
echo                      Story/Table freshness and fails closed after a game
echo                      update; use --from-game --with-assets then.
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
echo                      Rejected by scopes that skip Story evidence.
echo.
echo Examples:
echo   export.bat
echo   export.bat --from-game
echo   export.bat --from-game --with-assets --focused-assets
echo   export.bat --assets-only --from-game --focused-assets
echo   export.bat --from-game --game-root "E:\Games\Endfield Game\Endfield_Data"
echo   python -m scripts.story_builder.protocol_registry --ensure-current
echo   python -m scripts.build_mission_pipeline_data --refresh-source-story-gap-queue
echo   python -m scripts.build_map_recovery_data --with-preview
echo.
echo Notes:
echo   For repeated runs, edit endfield_paths.bat instead of passing --game-root.
echo   Story sort order in webui\overrides\story_order.json is yours to manage;
echo   export.bat never rewrites it.
echo   Every run writes a wall-time and RAM benchmark under reports\export.
echo   --assets-only runs are labelled export_assets there.
echo   The configured ENDFIELD_EXPORT_ROOT is used by extraction and builders.
echo   Static world scene chunks need the structured export, so use
echo   "export.bat --from-game --world-scene-chunk MAP:X:Z" for those.
echo   With --from-game, any other option is passed to
echo   scripts\export_full_from_game.py. That is where the --animestudio-*
echo   tuning and --world-scene-chunk MAP:X:Z live; run
echo   "python scripts\export_full_from_game.py --help" to see them.
echo Companion wrappers:
echo   export_assets.bat  Thin wrapper for --assets-only.
echo   build_updates.bat  Build the Updates tab feed.
echo   python scripts\pack_webui.py
echo                      Create split shareable WebUI zips.
echo.
endlocal
exit /b 0
