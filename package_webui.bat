@echo off
setlocal

python .\scripts\webui\package_webui.py %*
if errorlevel 1 exit /b %errorlevel%

endlocal
