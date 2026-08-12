@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PROJECT_DIR=%~dp0"
set "PROJECT_PATH=%PROJECT_DIR:~0,-1%"
set "UNITY_EXE=D:\Program Files\2022.3.62f3\Editor\Unity.exe"
set "METHOD=EndfieldGraphShaderLabEditor.EndfieldManifestCharacterSetup.RenderRuntimeReferenceWulfaPreview"
set "OUTPUT_ROOT=%PROJECT_PATH%\scratch\character_recovery\deferred_gbuffer_frame"

if not exist "%UNITY_EXE%" (
  echo Unity editor not found: %UNITY_EXE%
  exit /b 1
)
if not exist "%OUTPUT_ROOT%" mkdir "%OUTPUT_ROOT%"

set "ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE=1"
set "ENDFIELD_RECOVERED_EYE_RESPONSE_SEMANTICS=1"
set "ENDFIELD_RECOVERED_FACE_HIGHLIGHT_SEMANTICS=1"
set "ENDFIELD_RECOVERED_POST_SEMANTICS=1"
set "ENDFIELD_RECOVERED_SEPARATE_CHARACTER_SHADOW=1"
set "ENDFIELD_RECOVERED_CLUSTERED_NPR_LIGHT_LOOP=1"
set "ENDFIELD_RECOVERED_LIGHT_BINNING_MEMBERSHIP=1"
set "ENDFIELD_RECOVERED_ISOLATED_PUNCTUAL_SOFT_SHADOWS=1"
set "ENDFIELD_RECOVERED_PUNCTUAL_SHADOW_TILE_RESOLUTION=1024"
set "ENDFIELD_RECOVERED_CHARINFO_READY_SUBSET_DIAGNOSTIC=1"
set "ENDFIELD_RECOVERED_CHARINFO_CUMULATIVE_DIAGNOSTIC=1"
set "ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT=0"
set "ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_MODE=off"
set "ENDFIELD_RECOVERED_CANONICAL_BINNING_BUFFER=1"
set "ENDFIELD_RECOVERED_VISIBILITY_SH=1"
set "ENDFIELD_RECOVERED_DEFERRED_GBUFFER_FRAME=1"

if /i "%~1"=="--all" (
  call :RUN d3d11
  set "RUN_EXIT=!ERRORLEVEL!"
  if not "!RUN_EXIT!"=="0" exit /b !RUN_EXIT!
  call :RUN d3d12
  set "RUN_EXIT=!ERRORLEVEL!"
  exit /b !RUN_EXIT!
)
if /i "%~1"=="--d3d11" (
  call :RUN d3d11
  set "RUN_EXIT=!ERRORLEVEL!"
  exit /b !RUN_EXIT!
)
if /i "%~1"=="--d3d12" (
  call :RUN d3d12
  set "RUN_EXIT=!ERRORLEVEL!"
  exit /b !RUN_EXIT!
)
if /i "%~1"=="--fail-closed-d3d12" (
  call :RUN_FAIL_CLOSED d3d12
  set "RUN_EXIT=!ERRORLEVEL!"
  exit /b !RUN_EXIT!
)
if /i "%~1"=="--resolver-input-d3d12" (
  call :RUN_RESOLVER_INPUT d3d12
  set "RUN_EXIT=!ERRORLEVEL!"
  exit /b !RUN_EXIT!
)
if /i "%~1"=="--resolver-input-d3d11" (
  call :RUN_RESOLVER_INPUT d3d11
  set "RUN_EXIT=!ERRORLEVEL!"
  exit /b !RUN_EXIT!
)
if /i "%~1"=="--resolver-resource-d3d12" (
  call :RUN_RESOURCES d3d12
  set "RUN_EXIT=!ERRORLEVEL!"
  exit /b !RUN_EXIT!
)
if /i "%~1"=="--resolver-resource-d3d11" (
  call :RUN_RESOURCES d3d11
  set "RUN_EXIT=!ERRORLEVEL!"
  exit /b !RUN_EXIT!
)
if /i "%~1"=="--exact-consumer-d3d11" (
  call :RUN_EXACT_CONSUMER d3d11
  set "RUN_EXIT=!ERRORLEVEL!"
  exit /b !RUN_EXIT!
)

echo Usage: %~nx0 --all ^| --d3d11 ^| --d3d12 ^| --fail-closed-d3d12 ^| --resolver-input-d3d11 ^| --resolver-input-d3d12 ^| --resolver-resource-d3d11 ^| --resolver-resource-d3d12 ^| --exact-consumer-d3d11
exit /b 2

:RUN
set "API=%~1"
set "LOG_PATH=%OUTPUT_ROOT%\unity_validation_!API!.log"
set "REPORT_PATH=%OUTPUT_ROOT%\gpu_validation_!API!.json"
set "BEAUTY_PATH=%OUTPUT_ROOT%\wulfa_beauty_!API!.png"
echo Validating same-camera SphereOutside HGBuffer frame with !API!...
"%UNITY_EXE%" -batchmode -quit -projectPath "%PROJECT_PATH%" -force-!API! -executeMethod %METHOD% -logFile "!LOG_PATH!"
set "UNITY_EXIT=!ERRORLEVEL!"
if not "!UNITY_EXIT!"=="0" exit /b !UNITY_EXIT!
copy /y "%PROJECT_PATH%\..\scratch\runtime_reference_wulfa.png" "!BEAUTY_PATH!" >nul
set "COPY_EXIT=!ERRORLEVEL!"
if not "!COPY_EXIT!"=="0" exit /b !COPY_EXIT!
python "%PROJECT_PATH%\tools\verify_deferred_gbuffer_frame_log.py" --api !API! --log "!LOG_PATH!" --report "!REPORT_PATH!" --beauty "!BEAUTY_PATH!"
set "VERIFY_EXIT=!ERRORLEVEL!"
exit /b !VERIFY_EXIT!

:RUN_FAIL_CLOSED
set "API=%~1"
set "LOG_PATH=%OUTPUT_ROOT%\unity_fail_closed_!API!.log"
set "REPORT_PATH=%OUTPUT_ROOT%\gpu_fail_closed_!API!.json"
set "BEAUTY_PATH=%OUTPUT_ROOT%\wulfa_beauty_fail_closed_!API!.png"
set "ENDFIELD_RECOVERED_CANONICAL_BINNING_BUFFER=0"
echo Validating fail-closed SphereOutside HGBuffer frame with !API!...
"%UNITY_EXE%" -batchmode -quit -projectPath "%PROJECT_PATH%" -force-!API! -executeMethod %METHOD% -logFile "!LOG_PATH!"
set "UNITY_EXIT=!ERRORLEVEL!"
if not "!UNITY_EXIT!"=="0" exit /b !UNITY_EXIT!
copy /y "%PROJECT_PATH%\..\scratch\runtime_reference_wulfa.png" "!BEAUTY_PATH!" >nul
set "COPY_EXIT=!ERRORLEVEL!"
if not "!COPY_EXIT!"=="0" exit /b !COPY_EXIT!
python "%PROJECT_PATH%\tools\verify_deferred_gbuffer_frame_log.py" --api !API! --log "!LOG_PATH!" --report "!REPORT_PATH!" --beauty "!BEAUTY_PATH!" --expect-fail-closed
set "VERIFY_EXIT=!ERRORLEVEL!"
exit /b !VERIFY_EXIT!

:RUN_RESOLVER_INPUT
set "API=%~1"
set "ENDFIELD_RECOVERED_DEFERRED_RESOLVER_INPUT_PROBE=1"
set "LOG_PATH=%OUTPUT_ROOT%\unity_resolver_input_!API!.log"
set "REPORT_PATH=%OUTPUT_ROOT%\resolver_input_validation_!API!.json"
echo Validating same-frame deferred resolver input probe with !API!...
"%UNITY_EXE%" -batchmode -quit -projectPath "%PROJECT_PATH%" -force-!API! -executeMethod %METHOD% -logFile "!LOG_PATH!"
set "UNITY_EXIT=!ERRORLEVEL!"
if not "!UNITY_EXIT!"=="0" exit /b !UNITY_EXIT!
python "%PROJECT_PATH%\tools\verify_deferred_resolver_input_probe.py" --log "!LOG_PATH!" --report "!REPORT_PATH!"
exit /b !ERRORLEVEL!

:RUN_RESOURCES
set "API=%~1"
set "ENDFIELD_RECOVERED_DEFERRED_RESOLVER_RESOURCE_PROBE=1"
set "ENDFIELD_RECOVERED_LOW_RES_DIRECTIONAL_SHADOW=1"
set "ENDFIELD_RECOVERED_SCREEN_SHADOW_R_ATTACHMENT_DIAGNOSTIC=1"
set "LOG_PATH=%OUTPUT_ROOT%\unity_resolver_resource_!API!.log"
set "REPORT_PATH=%OUTPUT_ROOT%\resolver_resource_validation_!API!.json"
echo Validating same-frame deferred resolver target resources with !API!...
"%UNITY_EXE%" -batchmode -quit -projectPath "%PROJECT_PATH%" -force-!API! -executeMethod %METHOD% -logFile "!LOG_PATH!"
set "UNITY_EXIT=!ERRORLEVEL!"
if not "!UNITY_EXIT!"=="0" exit /b !UNITY_EXIT!
python "%PROJECT_PATH%\tools\verify_deferred_resolver_input_probe.py" --log "!LOG_PATH!" --report "!REPORT_PATH!" --expect-resource-probe
exit /b !ERRORLEVEL!

:RUN_EXACT_CONSUMER
set "API=%~1"
set "ENDFIELD_RECOVERED_DEFERRED_EXACT_CONSUMER=1"
set "ENDFIELD_RECOVERED_LOW_RES_DIRECTIONAL_SHADOW=1"
set "ENDFIELD_RECOVERED_SCREEN_SHADOW_R_ATTACHMENT_DIAGNOSTIC=1"
set "LOG_PATH=%OUTPUT_ROOT%\unity_exact_consumer_!API!.log"
set "REPORT_PATH=%OUTPUT_ROOT%\exact_consumer_validation_!API!.json"
echo Validating exact original deferred resolver consumer with !API!...
"%UNITY_EXE%" -batchmode -quit -projectPath "%PROJECT_PATH%" -force-!API! -executeMethod %METHOD% -logFile "!LOG_PATH!"
set "UNITY_EXIT=!ERRORLEVEL!"
if not "!UNITY_EXIT!"=="0" exit /b !UNITY_EXIT!
python "%PROJECT_PATH%\tools\verify_deferred_exact_consumer.py" --log "!LOG_PATH!" --report "!REPORT_PATH!"
exit /b !ERRORLEVEL!
