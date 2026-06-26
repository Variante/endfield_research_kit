@echo off
setlocal

set "EXPORT_ARGS="
set "VERIFY_EXPORT_ARGS="
set "EXPORT_FROM_GAME=0"

if exist "%~dp0endfield_paths.bat" call "%~dp0endfield_paths.bat"
if errorlevel 1 exit /b %errorlevel%
if defined ENDFIELD_GAME_ROOT set "EXPORT_ARGS=%EXPORT_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""
if defined ENDFIELD_GAME_ROOT set "VERIFY_EXPORT_ARGS=%VERIFY_EXPORT_ARGS% --game-root "%ENDFIELD_GAME_ROOT%""

:parse_args
if "%~1"=="" goto :parsed_args
if /I "%~1"=="--help" goto :help
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
  set "VERIFY_EXPORT_ARGS=%VERIFY_EXPORT_ARGS% "%~1" "%~2""
  shift
  shift
  goto :parse_args
)
set "EXPORT_ARGS=%EXPORT_ARGS% "%~1""
shift
goto :parse_args

:parsed_args
rem WebUI export/build pipeline:
rem - rebuild from existing export_full by default
rem - export from the installed game only when explicitly requested
rem - skip raw_vfs, source inventory, structured data, and AnimeStudio by default
rem - build only CN story/reference data by default
rem - preserve OCR-managed Story sort order under webui\overrides
rem - leave decoded CN audio relinking to export_assets.bat
rem - skip image/model asset decoding; use export_assets.bat --export-from-game for that
if "%EXPORT_FROM_GAME%"=="0" goto :skip_export_full
python .\scripts\export_full_from_game.py --animestudio-scope story --animestudio-stages maps json_by_type %EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :after_export_full

:skip_export_full
echo [export.bat] Reusing existing export_full; pass --export-from-game to refresh from installed game data.

:after_export_full

python .\scripts\verify_export_freshness.py %VERIFY_EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\refresh_evidence.py
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\build.py --languages CN --default-language CN --skip-audio-link
if errorlevel 1 exit /b %errorlevel%

endlocal
exit /b 0

:help
echo Usage: export.bat [--export-from-game] [--game-root PATH] [export_full_from_game.py options]
echo.
echo Runs the story/reference WebUI refresh from existing export_full by default,
echo verifies export freshness, rebuilds source-link evidence, builds CN data,
echo and preserves OCR-managed Story sort order. Use export_assets.bat to
echo refresh Assets tab data and relink decoded Story audio.
echo Reading installed game data and tool-based extraction are opt-in.
echo.
echo   --export-from-game    Refresh export_full from installed game data.
echo   --game-root PATH      Installed Endfield_Data directory used for export,
echo                         and freshness verification.
echo   --animestudio-jobs N  Passed through when --export-from-game is present.
echo                         Default is 4 for parallel shard/type export.
echo                         Lower this value if peak AnimeStudio memory is too high.
echo   --animestudio-dummy-dlls PATH
echo                         DummyDll directory for AnimeStudio MonoBehaviour schema recovery.
echo                         Can also be set with ANIMESTUDIO_DUMMY_DLLS.
echo.
echo If Endfield is installed somewhere else, pass --game-root.
echo For repeated runs, edit endfield_paths.bat instead.
echo Example:
echo   export.bat --export-from-game --game-root "E:\Games\Endfield Game\Endfield_Data"
echo.
echo Other arguments are passed to scripts\export_full_from_game.py only when
echo --export-from-game is present. The wrapper also forwards --game-root to
echo the freshness verifier.
echo.
echo Companion wrappers:
echo   build_updates.bat     Build the Updates tab feed.
echo   export_assets.bat     Rebuild asset indexes/audio; pass --export-from-game to decode them.
echo   package_webui.bat     Create split shareable WebUI zips.
echo.
endlocal
exit /b 0
