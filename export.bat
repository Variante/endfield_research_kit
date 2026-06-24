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
set "GAME_ROOT_SPECIFIED=0"

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
  set "GAME_ROOT_SPECIFIED=1"
  set "EXPORT_ARGS=%EXPORT_ARGS% "%~1" "%~2""
  set "VERIFY_EXPORT_ARGS=%VERIFY_EXPORT_ARGS% "%~1" "%~2""
  set "AUDIO_ARGS=%AUDIO_ARGS% "%~1" "%~2""
  shift
  shift
  goto :parse_args
)
set "ARG=%~1"
if /I "%ARG:~0,12%"=="--game-root=" (
  set "GAME_ROOT_SPECIFIED=1"
  set "EXPORT_ARGS=%EXPORT_ARGS% "%~1""
  set "VERIFY_EXPORT_ARGS=%VERIFY_EXPORT_ARGS% "%~1""
  set "AUDIO_ARGS=%AUDIO_ARGS% "%~1""
  shift
  goto :parse_args
)
set "EXPORT_ARGS=%EXPORT_ARGS% "%~1""
shift
goto :parse_args

:parsed_args
if "%GAME_ROOT_SPECIFIED%"=="0" if not "%ENDFIELD_GAME_ROOT%"=="" (
  set "EXPORT_ARGS=%EXPORT_ARGS% "--game-root" "%ENDFIELD_GAME_ROOT%""
  set "VERIFY_EXPORT_ARGS=%VERIFY_EXPORT_ARGS% "--game-root" "%ENDFIELD_GAME_ROOT%""
  set "AUDIO_ARGS=%AUDIO_ARGS% "--game-root" "%ENDFIELD_GAME_ROOT%""
)

rem WebUI export/build pipeline:
rem - rebuild from existing export_full by default
rem - export from the installed game only when explicitly requested
rem - skip raw_vfs, source inventory, structured data, and AnimeStudio by default
rem - build only CN story/reference data by default
rem - preserve OCR-managed Story sort order under webui\overrides
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

python .\scripts\story_builder\build.py --languages CN --default-language CN --skip-audio-link
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
echo Usage: export.bat [--export-from-game] [--game-root PATH] [export_full_from_game.py options]
echo.
echo Runs the story/reference WebUI refresh from existing export_full by default,
echo verifies export freshness, rebuilds source-link evidence, builds CN data,
echo preserves OCR-managed Story sort order, and links decoded Story audio.
echo Reading installed game data and tool-based extraction are opt-in.
echo.
echo   --export-from-game    Refresh export_full and decode audio from installed game data.
echo   --game-root PATH      Installed Endfield_Data directory used for export,
echo                         freshness verification, and audio decoding/linking.
echo   --animestudio-jobs N  Passed through when --export-from-game is present.
echo                         Default is 1 for lower peak AnimeStudio memory.
echo                         On the 64 GB test machine, 2 was the best tested value.
echo   --animestudio-dummy-dlls PATH
echo                         DummyDll directory for AnimeStudio MonoBehaviour schema recovery.
echo                         Can also be set with ANIMESTUDIO_DUMMY_DLLS.
echo.
echo If Endfield is installed somewhere else, pass --game-root or set
echo ENDFIELD_GAME_ROOT. The command-line --game-root value takes precedence.
echo Example:
echo   export.bat --export-from-game --game-root "E:\Games\Endfield Game\Endfield_Data"
echo.
echo Other arguments are passed to scripts\export_full_from_game.py only when
echo --export-from-game is present. The wrapper also forwards --game-root to
echo the freshness verifier and audio builder.
echo.
echo Companion wrappers:
echo   build_updates.bat     Build the Updates tab feed.
echo   export_assets.bat     Rebuild asset indexes; pass --export-from-game to decode assets.
echo   package_webui.bat     Create split shareable WebUI zips.
echo.
endlocal
exit /b 0
