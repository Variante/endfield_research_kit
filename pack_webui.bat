@echo off
python "%~dp0scripts\pack_webui.py" %*
exit /b %errorlevel%
