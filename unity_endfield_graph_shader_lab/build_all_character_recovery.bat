@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "PROJECT_PATH=%PROJECT_DIR:~0,-1%"
set "UNITY_EXE=D:\Program Files\2022.3.62f3\Editor\Unity.exe"
set "BUILD_METHOD=EndfieldGraphShaderLabEditor.EndfieldCharacterRecoverySetup.BuildAllCharacters"
set "LOG_DIR=%PROJECT_DIR%scratch\character_recovery\build_all"
set "LOG_PATH=%LOG_DIR%\unity_build.log"
set "ACL_JOB_DIR=%PROJECT_DIR%tmp\character_recovery\endminf_source_rebuild"
set "ACL_JOB_PATH=%ACL_JOB_DIR%\acl_import_job.json"

if not exist "%UNITY_EXE%" (
  echo Unity 2022.3.62f3 not found at "%UNITY_EXE%".
  exit /b 1
)

python "%PROJECT_DIR%tools\prepare_endminf_source_rebuild.py" --output-root "%ACL_JOB_DIR%"
if errorlevel 1 (
  echo Endminf source rebuild preflight failed before Unity launch.
  exit /b 1
)
if not exist "%ACL_JOB_PATH%" (
  echo Endminf ACL import job was not written: "%ACL_JOB_PATH%".
  exit /b 1
)

set "ENDFIELD_RECOVERED_ACL_IMPORT_JOB=%ACL_JOB_PATH%"
set "ENDFIELD_ENDMINF_VISUAL_COMPATIBILITY=1"
set "ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT=1"

:wait_for_project
set "PROJECT_BUSY="
if exist "%PROJECT_DIR%Temp\UnityLockfile" set "PROJECT_BUSY=UnityLockfile"
tasklist /FI "IMAGENAME eq Unity.exe" 2>nul | find /I "Unity.exe" >nul && set "PROJECT_BUSY=Unity.exe"
tasklist /FI "IMAGENAME eq UnityHub.exe" 2>nul | find /I "UnityHub.exe" >nul && set "PROJECT_BUSY=UnityHub.exe"
tasklist /FI "IMAGENAME eq Endfield.exe" 2>nul | find /I "Endfield.exe" >nul && set "PROJECT_BUSY=Endfield.exe"
if defined PROJECT_BUSY (
  echo Character recovery Unity project is in use ^(%PROJECT_BUSY%^); retrying in 15 seconds.
  timeout /t 15 /nobreak >nul
  goto wait_for_project
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

"%UNITY_EXE%" -batchmode -quit -projectPath "%PROJECT_PATH%" -force-d3d11 -executeMethod %BUILD_METHOD% -logFile "%LOG_PATH%"
set "EXIT_CODE=%ERRORLEVEL%"
echo Unity log: %LOG_PATH%
exit /b %EXIT_CODE%
