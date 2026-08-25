@echo off
setlocal

set "LAB_ROOT=%~dp0"
set "TRACE_PY=%LAB_ROOT%..\tools\frida-runtime\venv\Scripts\python.exe"
set "TRACE_SCRIPT=%LAB_ROOT%tools\burst_resolver_telemetry.py"
set "GAME_ROOT=%~1"
if not defined GAME_ROOT set "GAME_ROOT=D:\Program Files\Endfield Game"

if not exist "%TRACE_PY%" (
  echo Missing pinned Frida Python environment:
  echo   %TRACE_PY%
  exit /b 1
)

if not exist "%TRACE_SCRIPT%" (
  echo Missing Burst resolver telemetry script:
  echo   %TRACE_SCRIPT%
  exit /b 1
)

tasklist /fi "imagename eq Endfield.exe" 2>nul | find /i "Endfield.exe" >nul
if not errorlevel 1 (
  echo Endfield.exe is already running.
  echo Close the game normally, then run this launcher before the next startup so
  echo the observer can see the Burst resolver calls made during initialization.
  exit /b 1
)

echo Checking the exact installed native files before attaching...
"%TRACE_PY%" "%TRACE_SCRIPT%" --check-only --game-root "%GAME_ROOT%"
if errorlevel 1 exit /b 1

echo.
echo Observer ready. Start Endfield through its normal launcher now.
echo Navigate to Endminf's Character Info overview and let the loop run briefly.
echo Return here and press Ctrl+C once the pose has settled.
echo This trace observes LoadLibraryW and GetProcAddress only; it does not call a
echo returned pointer, replace code, or write game state.
echo.
"%TRACE_PY%" "%TRACE_SCRIPT%" --game-root "%GAME_ROOT%" --start-immediately
set "TRACE_EXIT=%ERRORLEVEL%"

if not "%TRACE_EXIT%"=="0" (
  echo.
  echo Burst resolver telemetry ended with exit code %TRACE_EXIT%.
  echo Do not retry through an attach refusal or protection termination.
  exit /b %TRACE_EXIT%
)

echo.
echo Burst resolver telemetry completed. Output is under:
echo   scratch\reverse_engineering\burst_resolver_telemetry
exit /b 0
