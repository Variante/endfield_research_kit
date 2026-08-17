@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PROJECT_PATH=%PROJECT_DIR:~0,-1%"
if not defined UNITY_EXE set "UNITY_EXE=D:\Program Files\2022.3.62f3\Editor\Unity.exe"
set "BUILD_METHOD=EndfieldGraphShaderLabEditor.EndfieldOriginalM23DxbcDiagnosticBuilder.BuildAndValidate"
set "D3D12_METHOD=EndfieldGraphShaderLabEditor.EndfieldOriginalM23DxbcDiagnosticBuilder.ValidateD3D12NonActivation"
set "OUTPUT_DIR=%PROJECT_PATH%\scratch\reverse_engineering\original_m23_dxbc_exact_diagnostic"
set "EDITOR_LOG=%OUTPUT_DIR%\editor_d3d11.log"
set "D3D12_LOG=%OUTPUT_DIR%\editor_d3d12.log"
set "PLAYER_LOG=%OUTPUT_DIR%\standalone_d3d11.log"
set "PLAYER_EXE=%PROJECT_PATH%\Builds\OriginalM23DxbcExactDiagnostic\EndfieldOriginalM23DxbcExactDiagnostic.exe"
set "PLAYER_REPORT=%OUTPUT_DIR%\standalone_validation.json"
set "D3D12_REPORT=%OUTPUT_DIR%\d3d12_non_activation.json"
set "VISUAL_GRID=0"
if /I "%~1"=="--visual-grid" set "VISUAL_GRID=1"

if not exist "%UNITY_EXE%" (
  echo Unity 2022.3.62f3 editor not found: %UNITY_EXE%
  exit /b 1
)
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
del /F /Q "%PLAYER_REPORT%" "%D3D12_REPORT%" "%OUTPUT_DIR%\standalone_validation.png" "%OUTPUT_DIR%\standalone_build.json" 2>nul

powershell -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_PATH%\tools\original_m23_dxbc_exact\build_plugin.ps1"
if errorlevel 1 exit /b %ERRORLEVEL%

"%UNITY_EXE%" -batchmode -quit -force-d3d11 -projectPath "%PROJECT_PATH%" -executeMethod %BUILD_METHOD% -endfield-original-m23-dxbc-diagnostic -logFile "%EDITOR_LOG%"
set "EDITOR_EXIT=%ERRORLEVEL%"
if not "%EDITOR_EXIT%"=="0" exit /b %EDITOR_EXIT%
if not exist "%PLAYER_EXE%" exit /b 3

set "VISUAL_ARGUMENT="
if "%VISUAL_GRID%"=="1" set "VISUAL_ARGUMENT=-endfield-original-m23-dxbc-visual-grid"
if "%VISUAL_GRID%"=="1" pushd "%PROJECT_PATH%\tools\original_m23_dxbc_exact"
"%PLAYER_EXE%" -batchmode -force-d3d11 -screen-width 1 -screen-height 1 -endfield-original-m23-dxbc-diagnostic %VISUAL_ARGUMENT% -endfield-original-m23-dxbc-output "%PLAYER_REPORT%" -logFile "%PLAYER_LOG%"
set "PLAYER_EXIT=%ERRORLEVEL%"
if "%VISUAL_GRID%"=="1" popd

"%UNITY_EXE%" -batchmode -quit -force-d3d12 -projectPath "%PROJECT_PATH%" -executeMethod %D3D12_METHOD% -endfield-original-m23-dxbc-diagnostic -endfield-original-m23-dxbc-output "%D3D12_REPORT%" -logFile "%D3D12_LOG%"
set "D3D12_EXIT=%ERRORLEVEL%"

set "VISUAL_TEST_ARGUMENT="
if "%VISUAL_GRID%"=="1" set "VISUAL_TEST_ARGUMENT=--visual-grid"
python "%PROJECT_PATH%\tools\test_original_m23_dxbc_exact_managed.py" --report "%PLAYER_REPORT%" --d3d12-report "%D3D12_REPORT%" %VISUAL_TEST_ARGUMENT%
set "CHECK_EXIT=%ERRORLEVEL%"
if not "%PLAYER_EXIT%"=="0" exit /b %PLAYER_EXIT%
if not "%D3D12_EXIT%"=="0" exit /b %D3D12_EXIT%
exit /b %CHECK_EXIT%
