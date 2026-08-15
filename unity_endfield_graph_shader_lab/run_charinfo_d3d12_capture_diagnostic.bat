@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PROJECT_PATH=%PROJECT_DIR:~0,-1%"
set "UNITY_EXE=D:\Program Files\2022.3.62f3\Editor\Unity.exe"
set "OUTPUT_DIR=%PROJECT_PATH%\scratch\character_recovery\charinfo_d3d12_capture"
set "OUTPUT_PATH=%OUTPUT_DIR%\diagnostic.json"
set "LOG_PATH=%OUTPUT_DIR%\unity.log"

if not exist "%UNITY_EXE%" exit /b 1
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
"%UNITY_EXE%" -batchmode -force-d3d12 -quit ^
  -projectPath "%PROJECT_PATH%" ^
  -endfield-charinfo-d3d12-output "%OUTPUT_PATH%" ^
  -executeMethod EndfieldGraphShaderLabEditor.EndfieldCharInfoD3D12CaptureDiagnostic.CaptureAndWrite ^
  -logFile "%LOG_PATH%"
set "EXIT_CODE=%ERRORLEVEL%"
echo Unity log: %LOG_PATH%
echo Diagnostic: %OUTPUT_PATH%
exit /b %EXIT_CODE%
