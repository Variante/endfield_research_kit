@echo off
setlocal EnableDelayedExpansion

set "PROJECT_DIR=%~dp0"
set "PROJECT_PATH=%PROJECT_DIR:~0,-1%"
if not defined UNITY_EXE set "UNITY_EXE=D:\Program Files\2022.3.62f3\Editor\Unity.exe"
set "METHOD=EndfieldGraphShaderLabEditor.EndfieldRecoveredDeferredLightDataBatchVerifier.VerifyBatch"
set "FRAME_METHOD=EndfieldGraphShaderLabEditor.EndfieldManifestCharacterSetup.RenderRuntimeReferenceWulfaPreview"
set "OUTPUT_DIR=%PROJECT_PATH%\scratch\character_recovery\deferred_light_data"

if not exist "%UNITY_EXE%" exit /b 1
if exist "%PROJECT_PATH%\Temp\UnityLockfile" (
  echo Unity project is already open; refusing to start a second editor.
  exit /b 2
)
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

set "ENDFIELD_RECOVERED_DEFERRED_TRANSFORM_VARIABLES=1"
set "ENDFIELD_RECOVERED_DEFERRED_LIGHT_DATA=1"
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

python "%PROJECT_PATH%\tools\audit_deferred_light_data.py" --check
if errorlevel 1 exit /b !ERRORLEVEL!

call :run_gpu d3d11
if errorlevel 1 exit /b !ERRORLEVEL!
call :run_gpu d3d12
if errorlevel 1 exit /b !ERRORLEVEL!
call :run_frame d3d11
if errorlevel 1 exit /b !ERRORLEVEL!
call :run_frame d3d12
if errorlevel 1 exit /b !ERRORLEVEL!
set "ENDFIELD_RECOVERED_CANONICAL_BINNING_BUFFER=0"
call :run_fail_closed d3d12
if errorlevel 1 exit /b !ERRORLEVEL!
python "%PROJECT_PATH%\tools\verify_deferred_light_data.py" --root "%OUTPUT_DIR%"
exit /b !ERRORLEVEL!

:run_gpu
set "API=%~1"
"%UNITY_EXE%" -batchmode -quit -force-%API% -projectPath "%PROJECT_PATH%" -executeMethod %METHOD% -logFile "%OUTPUT_DIR%\unity_validation_%API%.log"
exit /b %ERRORLEVEL%

:run_frame
set "API=%~1"
"%UNITY_EXE%" -batchmode -quit -force-%API% -projectPath "%PROJECT_PATH%" -executeMethod %FRAME_METHOD% -logFile "%OUTPUT_DIR%\unity_frame_%API%.log"
if errorlevel 1 exit /b !ERRORLEVEL!
copy /y "%PROJECT_PATH%\..\scratch\runtime_reference_wulfa.png" "%OUTPUT_DIR%\wulfa_beauty_%API%.png" >nul
exit /b %ERRORLEVEL%

:run_fail_closed
set "API=%~1"
"%UNITY_EXE%" -batchmode -quit -force-%API% -projectPath "%PROJECT_PATH%" -executeMethod %FRAME_METHOD% -logFile "%OUTPUT_DIR%\unity_fail_closed_%API%.log"
if errorlevel 1 exit /b !ERRORLEVEL!
copy /y "%PROJECT_PATH%\..\scratch\runtime_reference_wulfa.png" "%OUTPUT_DIR%\wulfa_beauty_fail_closed_%API%.png" >nul
exit /b %ERRORLEVEL%
