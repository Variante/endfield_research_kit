@echo off
setlocal
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
python -m scripts.pack_webui %*
exit /b %errorlevel%
