@echo off
setlocal

python .\scripts\package_webui.py %*
if errorlevel 1 exit /b %errorlevel%

endlocal
