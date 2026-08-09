@echo off
setlocal EnableDelayedExpansion

set "PROJECT_DIR=%~dp0"
set "PROJECT_PATH=%PROJECT_DIR:~0,-1%"
if not defined UNITY_EXE set "UNITY_EXE=D:\Program Files\2022.3.62f3\Editor\Unity.exe"
set "METHOD=EndfieldGraphShaderLabEditor.EndfieldRecoveredCanonicalBinningBatchVerifier.VerifyBatch"
set "OUTPUT_DIR=%PROJECT_PATH%\scratch\character_recovery\canonical_binning_buffer"
set "MODE=%~1"
if "%MODE%"=="" set "MODE=--all"

if not exist "%UNITY_EXE%" (
  echo Unity 2022.3.62f3 editor not found: %UNITY_EXE%
  exit /b 1
)
if exist "%PROJECT_PATH%\Temp\UnityLockfile" (
  powershell -NoProfile -Command "if (Get-Process -Name Unity -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
  if not errorlevel 1 (
    echo Unity project is already open; refusing to start a second editor.
    exit /b 2
  )
  echo Removing stale Unity lock left by an exited process.
  del /F /Q "%PROJECT_PATH%\Temp\UnityLockfile"
)
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

if /I "%MODE%"=="--d3d11" (
  call :run_api d3d11
  exit /b !ERRORLEVEL!
)
if /I "%MODE%"=="--d3d12" (
  call :run_api d3d12
  exit /b !ERRORLEVEL!
)
if /I not "%MODE%"=="--all" (
  echo Usage: %~nx0 [--all^|--d3d11^|--d3d12]
  exit /b 64
)

call :run_api d3d11
if errorlevel 1 exit /b %ERRORLEVEL%
call :run_api d3d12
exit /b %ERRORLEVEL%

:run_api
set "API=%~1"
set "LOG_PATH=%OUTPUT_DIR%\unity_validation_%API%.log"
echo Validating recovered canonical _BinningBuffer with %API%...
"%UNITY_EXE%" -batchmode -quit -force-%API% -projectPath "%PROJECT_PATH%" -executeMethod %METHOD% -logFile "%LOG_PATH%"
set "RUN_EXIT=%ERRORLEVEL%"
echo Unity log: %LOG_PATH%
echo Validation report: %OUTPUT_DIR%\gpu_validation_%API%.json
exit /b %RUN_EXIT%
