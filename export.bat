@echo off
setlocal

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="/h" goto :help
if /I "%~1"=="help" goto :help

set "EXPORT_ARGS="
set "VERIFY_EXPORT_ARGS="
set "AUDIO_ARGS="
set "EXPORT_FROM_GAME=0"

:parse_args
if "%~1"=="" goto :parsed_args
if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="/h" goto :help
if /I "%~1"=="help" goto :help
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
  set "AUDIO_ARGS=%AUDIO_ARGS% "%~1" "%~2""
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
rem - build recovered story file order for the WebUI Story sort
rem - finally rebuild/link CN audio, decoding first only for --export-from-game
rem - skip image/model/animation asset decoding; use export_assets.bat --export-from-game for that
if "%EXPORT_FROM_GAME%"=="0" goto :skip_export_full
python .\scripts\export_full_from_game.py --animestudio-scope story --animestudio-stages maps json_by_type %EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :after_export_full

:skip_export_full
echo [export.bat] Reusing existing export_full; pass --export-from-game to refresh from installed game data.

:after_export_full

python .\scripts\verify_export_freshness.py %VERIFY_EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\dialog_registry.py --quiet
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\video_bindings.py
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\source_links.py
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_builder\build.py --languages CN --default-language CN
if errorlevel 1 exit /b %errorlevel%

python .\scripts\story_recovery\build_story_order.py
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

:help
echo Usage: export.bat [--export-from-game] [export_full_from_game.py options]
echo.
echo Runs the story/reference WebUI refresh from existing export_full by default,
echo verifies export freshness, rebuilds source-link evidence, builds CN data,
echo refreshes Story sort order, and links decoded Story audio.
echo Reading installed game data and tool-based extraction are opt-in.
echo.
echo   --export-from-game    Refresh export_full and decode audio from installed game data.
echo.
echo Other arguments are passed to scripts\export_full_from_game.py when
echo --export-from-game is present, or to the freshness verifier where relevant.
echo.
echo Companion wrappers:
echo   build_updates.bat     Build the Updates tab feed.
echo   export_assets.bat     Rebuild asset indexes; pass --export-from-game to decode assets.
echo   package_webui.bat     Create split shareable WebUI zips.
echo.
endlocal
exit /b 0
