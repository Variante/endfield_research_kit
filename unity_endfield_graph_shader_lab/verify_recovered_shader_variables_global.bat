@echo off
setlocal EnableDelayedExpansion

set "PROJECT_DIR=%~dp0"
set "PROJECT_PATH=%PROJECT_DIR:~0,-1%"
if not defined UNITY_EXE set "UNITY_EXE=D:\Program Files\2022.3.62f3\Editor\Unity.exe"
set "METHOD=EndfieldGraphShaderLabEditor.EndfieldRecoveredShaderVariablesGlobalBatchVerifier.VerifyBatch"
set "FRAME_METHOD=EndfieldGraphShaderLabEditor.EndfieldManifestCharacterSetup.RenderRuntimeReferenceWulfaPreview"
set "OUTPUT_DIR=%PROJECT_PATH%\scratch\character_recovery\shader_variables_global"
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

set "ENDFIELD_RECOVERED_SHADER_VARIABLES_GLOBAL=1"
set "ENDFIELD_RECOVERED_DEFERRED_TRANSFORM_VARIABLES=1"
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
python "%PROJECT_PATH%\tools\audit_deferred_shader_variables_global.py" --check
if errorlevel 1 exit /b !ERRORLEVEL!

if /I "%MODE%"=="--d3d11" (
  call :run_api d3d11
  if errorlevel 1 exit /b !ERRORLEVEL!
  call :run_frame d3d11
  exit /b !ERRORLEVEL!
)
if /I "%MODE%"=="--d3d12" (
  call :run_api d3d12
  if errorlevel 1 exit /b !ERRORLEVEL!
  call :run_frame d3d12
  exit /b !ERRORLEVEL!
)
if /I not "%MODE%"=="--all" (
  echo Usage: %~nx0 [--all^|--d3d11^|--d3d12]
  exit /b 64
)

call :run_api d3d11
if errorlevel 1 exit /b !ERRORLEVEL!
call :run_api d3d12
if errorlevel 1 exit /b !ERRORLEVEL!
call :run_frame d3d11
if errorlevel 1 exit /b !ERRORLEVEL!
call :run_frame d3d12
if errorlevel 1 exit /b !ERRORLEVEL!
call :run_fail_closed d3d12
if errorlevel 1 exit /b !ERRORLEVEL!
python "%PROJECT_PATH%\tools\verify_shader_variables_global.py" --root "%OUTPUT_DIR%"
exit /b !ERRORLEVEL!

:run_api
set "API=%~1"
set "LOG_PATH=%OUTPUT_DIR%\unity_validation_%API%.log"
echo Validating recovered ShaderVariablesGlobal with %API%...
"%UNITY_EXE%" -batchmode -quit -force-%API% -projectPath "%PROJECT_PATH%" -executeMethod %METHOD% -logFile "%LOG_PATH%"
set "RUN_EXIT=%ERRORLEVEL%"
echo Unity log: %LOG_PATH%
echo Validation report: %OUTPUT_DIR%\gpu_validation_%API%.json
exit /b %RUN_EXIT%

:run_frame
set "API=%~1"
set "LOG_PATH=%OUTPUT_DIR%\unity_frame_%API%.log"
set "BEAUTY_PATH=%OUTPUT_DIR%\wulfa_beauty_%API%.png"
echo Validating same-frame ShaderVariablesGlobal with %API%...
"%UNITY_EXE%" -batchmode -quit -force-%API% -projectPath "%PROJECT_PATH%" -executeMethod %FRAME_METHOD% -logFile "%LOG_PATH%"
set "RUN_EXIT=%ERRORLEVEL%"
if not "%RUN_EXIT%"=="0" exit /b %RUN_EXIT%
copy /y "%PROJECT_PATH%\..\scratch\runtime_reference_wulfa.png" "%BEAUTY_PATH%" >nul
exit /b %ERRORLEVEL%

:run_fail_closed
set "API=%~1"
set "LOG_PATH=%OUTPUT_DIR%\unity_fail_closed_%API%.log"
set "BEAUTY_PATH=%OUTPUT_DIR%\wulfa_beauty_fail_closed_%API%.png"
set "ENDFIELD_RECOVERED_CANONICAL_BINNING_BUFFER=0"
echo Validating fail-closed ShaderVariablesGlobal with %API%...
"%UNITY_EXE%" -batchmode -quit -force-%API% -projectPath "%PROJECT_PATH%" -executeMethod %FRAME_METHOD% -logFile "%LOG_PATH%"
set "RUN_EXIT=%ERRORLEVEL%"
if not "%RUN_EXIT%"=="0" exit /b %RUN_EXIT%
copy /y "%PROJECT_PATH%\..\scratch\runtime_reference_wulfa.png" "%BEAUTY_PATH%" >nul
exit /b %ERRORLEVEL%
