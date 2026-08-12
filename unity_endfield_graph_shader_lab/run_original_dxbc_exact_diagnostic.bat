@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PROJECT_PATH=%PROJECT_DIR:~0,-1%"
if not defined UNITY_EXE set "UNITY_EXE=D:\Program Files\2022.3.62f3\Editor\Unity.exe"
set "METHOD=EndfieldGraphShaderLabEditor.EndfieldOriginalDxbcDiagnosticBuilder.BuildAndValidate"
set "OUTPUT_DIR=%PROJECT_PATH%\scratch\reverse_engineering\original_dxbc_exact_diagnostic"
set "EDITOR_LOG=%OUTPUT_DIR%\editor.log"
set "PLAYER_LOG=%OUTPUT_DIR%\standalone.log"
set "PLAYER_EXE=%PROJECT_PATH%\Builds\OriginalDxbcExactDiagnostic\EndfieldOriginalDxbcExactDiagnostic.exe"
set "PLAYER_REPORT=%OUTPUT_DIR%\standalone_validation.json"

if not exist "%UNITY_EXE%" (
  echo Unity 2022.3.62f3 editor not found: %UNITY_EXE%
  exit /b 1
)
if exist "%PROJECT_PATH%\Temp\UnityLockfile" (
  powershell -NoProfile -Command "if (Get-Process -Name Unity -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
  if not errorlevel 1 (
    echo Unity project is already open; close or stop it before this isolated run.
    exit /b 2
  )
  echo Removing stale Unity lock left by an exited process.
  del /F /Q "%PROJECT_PATH%\Temp\UnityLockfile"
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
del /F /Q "%OUTPUT_DIR%\editor_validation.json" 2>nul
del /F /Q "%OUTPUT_DIR%\standalone_validation.json" 2>nul
del /F /Q "%OUTPUT_DIR%\standalone_build.json" 2>nul

powershell -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_PATH%\tools\original_dxbc_exact\build_plugin.ps1"
if errorlevel 1 exit /b %ERRORLEVEL%

"%UNITY_EXE%" -batchmode -quit -force-d3d11 -projectPath "%PROJECT_PATH%" -executeMethod %METHOD% -endfield-original-dxbc-diagnostic -logFile "%EDITOR_LOG%"
set "EDITOR_EXIT=%ERRORLEVEL%"
if not "%EDITOR_EXIT%"=="0" (
  echo Unity editor diagnostic/build failed with exit %EDITOR_EXIT%.
  python "%PROJECT_PATH%\tools\original_dxbc_exact\validate_diagnostic.py"
  exit /b %EDITOR_EXIT%
)

if not exist "%PLAYER_EXE%" (
  echo D3D11 diagnostic player was not built: %PLAYER_EXE%
  python "%PROJECT_PATH%\tools\original_dxbc_exact\validate_diagnostic.py"
  exit /b 3
)

"%PLAYER_EXE%" -batchmode -force-d3d11 -screen-width 1 -screen-height 1 -endfield-original-dxbc-diagnostic -endfield-original-dxbc-output "%PLAYER_REPORT%" -logFile "%PLAYER_LOG%"
set "PLAYER_EXIT=%ERRORLEVEL%"

python "%PROJECT_PATH%\tools\original_dxbc_exact\validate_diagnostic.py"
set "CHECK_EXIT=%ERRORLEVEL%"
echo Editor log: %EDITOR_LOG%
echo Standalone log: %PLAYER_LOG%
echo Editor report: %OUTPUT_DIR%\editor_validation.json
echo Standalone report: %PLAYER_REPORT%
if not "%PLAYER_EXIT%"=="0" exit /b %PLAYER_EXIT%
exit /b %CHECK_EXIT%
