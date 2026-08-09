@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PROJECT_PATH=%PROJECT_DIR:~0,-1%"
if not defined UNITY_EXE set "UNITY_EXE=D:\Program Files\2022.3.62f3\Editor\Unity.exe"
set "OUTPUT_ROOT=%PROJECT_PATH%\scratch\character_recovery\punctual_shadow_atlas_descriptor"
set "LOG_PATH=%OUTPUT_ROOT%\unity_probe.log"

if not exist "%UNITY_EXE%" (
  echo Unity editor not found: %UNITY_EXE%
  exit /b 1
)

if not exist "%OUTPUT_ROOT%" mkdir "%OUTPUT_ROOT%"
set "ENDFIELD_PUNCTUAL_SHADOW_ATLAS_PROBE_OUTPUT=%OUTPUT_ROOT%"

"%UNITY_EXE%" -batchmode -quit -force-d3d12 -projectPath "%PROJECT_PATH%" -executeMethod EndfieldGraphShaderLabEditor.EndfieldPunctualShadowAtlasDescriptorBatchProbe.Probe -logFile "%LOG_PATH%"
if errorlevel 1 exit /b %errorlevel%

if not exist "%OUTPUT_ROOT%\punctual_shadow_atlas_descriptor_probe.json" (
  echo Probe report was not written.
  exit /b 1
)

echo Punctual-shadow atlas descriptor probe passed.
echo Report: %OUTPUT_ROOT%\punctual_shadow_atlas_descriptor_probe.json
endlocal
