@echo off
setlocal

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="/h" goto :help
if /I "%~1"=="help" goto :help

set "EXPORT_ARGS="
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
  set "AUDIO_ARGS=%AUDIO_ARGS% "%~1" "%~2""
  shift
  shift
  goto :parse_args
)
set "ARG=%~1"
if /I "%ARG:~0,12%"=="--game-root=" (
  set "GAME_ROOT_SPECIFIED=1"
  set "EXPORT_ARGS=%EXPORT_ARGS% "%~1""
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
  set "AUDIO_ARGS=%AUDIO_ARGS% "--game-root" "%ENDFIELD_GAME_ROOT%""
)

rem Asset export/build pipeline:
rem - rebuild indexes from existing decoded assets by default
rem - export from the installed game only when explicitly requested
rem - skip structured story data and AnimeStudio by default
rem - build the WebUI Assets tab indexes and compact story media lookup
rem - rebuild/link CN audio, decoding first only for --export-from-game
if "%EXPORT_FROM_GAME%"=="0" goto :skip_export_full
python .\scripts\export_full_from_game.py --skip-structured --animestudio-scope assets --animestudio-stages convert_by_type json_by_type %EXPORT_ARGS%
if errorlevel 1 exit /b %errorlevel%
goto :after_export_full

:skip_export_full
echo [export_assets.bat] Reusing existing decoded assets; pass --export-from-game to refresh from installed game data.

:after_export_full

python .\scripts\build_assets.py
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
echo Usage: export_assets.bat [--export-from-game] [--game-root PATH] [export_full_from_game.py options]
echo.
echo Rebuilds WebUI Assets tab indexes plus the compact Story media lookup,
echo then relinks decoded CN Story audio. The heavier AnimeStudio
echo image/model/animation decode and CN audio decode are opt-in.
echo Story/reference data is handled by export.bat.
echo.
echo   --export-from-game    Run AnimeStudio image/model/animation conversion,
echo                         JSON export, and CN audio decode.
echo   --game-root PATH      Installed Endfield_Data directory used when
echo                         --export-from-game refreshes decoded assets/audio,
echo                         and for audio linking.
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
echo   export_assets.bat --export-from-game --game-root "E:\Games\Endfield Game\Endfield_Data"
echo.
echo Other arguments are passed to scripts\export_full_from_game.py when
echo --export-from-game is present. The wrapper also forwards --game-root to
echo the audio builder.
echo.
endlocal
exit /b 0
