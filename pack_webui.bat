@echo off
python "%~dp0scripts\pack_webui.py" --audio-format flac %*
exit /b %errorlevel%
