@echo off
setlocal
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
python -m scripts.webui.package %*
exit /b %errorlevel%
