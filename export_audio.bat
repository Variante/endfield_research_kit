@echo off
setlocal
cd /d "%~dp0"

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="/h" goto :help
if /I "%~1"=="help" goto :help

python scripts\build_audio.py %*
if errorlevel 1 exit /b %errorlevel%

endlocal
exit /b 0

:help
echo Usage: export_audio.bat [build_audio.py options]
echo.
echo Decodes Story audio with fluffy-dumper, writes webui\data\audio\LANG,
echo builds the WebUI audio index, parses Wwise event-to-media links, and
echo post-processes generated conversations with playable audioSrc links.
echo.
echo Common options:
echo   --skip-decode      Rebuild only indexes and Story links from existing decoded audio.
echo   --language CODE    Select CN, EN, JP, or KR. Default: CN.
echo   --format wav^|wem   Decode browser-ready WAVs by default, or keep WEM payloads.
echo   --block NAME       all, voice, audio, initial-audio, or audit-audio.
echo.
python scripts\build_audio.py --help
if errorlevel 1 (
  set "ERR=%errorlevel%"
  endlocal
  exit /b %ERR%
)
endlocal
exit /b 0
