@echo off
setlocal

set "LAB_ROOT=%~dp0"
set "TRACE_PY=%LAB_ROOT%..\tools\frida-runtime\venv\Scripts\python.exe"
set "TRACE_SCRIPT=%LAB_ROOT%tools\burst_resolver_telemetry.py"
set "VALIDATE_SCRIPT=%LAB_ROOT%tools\validate_burst_resolver_telemetry.py"
set "ROUTE_SCRIPT=%LAB_ROOT%tools\build_secondary_dynamics_calc_line_route_artifact.py"
set "OUTPUT_ROOT=%LAB_ROOT%..\scratch\reverse_engineering\burst_resolver_telemetry"
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

if not exist "%VALIDATE_SCRIPT%" (
  echo Missing Burst resolver telemetry validator:
  echo   %VALIDATE_SCRIPT%
  exit /b 1
)

if not exist "%ROUTE_SCRIPT%" (
  echo Missing CalcLine route artifact builder:
  echo   %ROUTE_SCRIPT%
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
echo This trace observes LoadLibraryW, GetProcAddress, and the returned live
echo pointers from six pinned BurstDirectCall wrappers. It does not call a
echo returned pointer, replace code, or write game state. Interceptor attachment
echo can perturb timing while the observer is active.
echo.
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMddTHHmmssfff"') do set "TRACE_STAMP=%%I"
if not defined TRACE_STAMP (
  echo Unable to allocate a unique trace name.
  exit /b 1
)
set "TRACE_OUTPUT=%OUTPUT_ROOT%\burst-resolver-%TRACE_STAMP%.jsonl"
set "VALIDATION_OUTPUT=%OUTPUT_ROOT%\burst-resolver-%TRACE_STAMP%.validation.json"
set "ROUTE_OUTPUT=%OUTPUT_ROOT%\burst-resolver-%TRACE_STAMP%.calc-line-route.json"

"%TRACE_PY%" "%TRACE_SCRIPT%" --game-root "%GAME_ROOT%" --start-immediately --output "%TRACE_OUTPUT%"
set "TRACE_EXIT=%ERRORLEVEL%"

if not "%TRACE_EXIT%"=="0" (
  echo.
  echo Burst resolver telemetry ended with exit code %TRACE_EXIT%.
  echo Do not retry through an attach refusal or protection termination.
  exit /b %TRACE_EXIT%
)

echo.
echo Validating the bounded trace...
"%TRACE_PY%" "%VALIDATE_SCRIPT%" "%TRACE_OUTPUT%" --output "%VALIDATION_OUTPUT%"
if errorlevel 1 exit /b 1

echo Building the immutable CalcLine route artifact...
"%TRACE_PY%" "%ROUTE_SCRIPT%" "%VALIDATION_OUTPUT%" --output "%ROUTE_OUTPUT%"
if errorlevel 1 (
  echo The trace is valid candidate evidence but does not close exactly one CalcLine route.
  echo Keep the trace and validation report; do not select a Unity route from them.
  exit /b 1
)

"%TRACE_PY%" "%ROUTE_SCRIPT%" "%VALIDATION_OUTPUT%" --output "%ROUTE_OUTPUT%" --check
if errorlevel 1 exit /b 1

echo.
echo Burst resolver telemetry and CalcLine route closure completed:
echo   Trace:      %TRACE_OUTPUT%
echo   Validation: %VALIDATION_OUTPUT%
echo   Route:      %ROUTE_OUTPUT%
exit /b 0
