@echo off
setlocal
pushd "%~dp0..\..\..\.."
set "ARGS=%*"
if /I "%~1"=="/?" set "ARGS=--help"
if /I "%~1"=="/h" set "ARGS=--help"
if /I "%~1"=="help" set "ARGS=--help"
python -m scripts.game_data.extraction.animestudio.setup_vgmstream %ARGS%
set "RC=%errorlevel%"
popd
exit /b %RC%
