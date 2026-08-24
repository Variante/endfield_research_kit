@echo off
setlocal
pushd "%~dp0\..\.."
python tools\reference_video_sequences.py %*
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
