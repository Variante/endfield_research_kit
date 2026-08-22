@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "UNITY_EXE=D:\Program Files\2022.3.62f3\Editor\Unity.exe"

if not exist "%UNITY_EXE%" (
  echo Unity 2022.3.62f3 not found at "%UNITY_EXE%".
  exit /b 1
)

if /i "%~1"=="--endminf-reproduction" (
  set "ENDFIELD_ENDMINF_VISUAL_COMPATIBILITY=1"
  set "ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT=1"
  set "ENDFIELD_ENDMINF_BACKDROP_VISUAL_COMPATIBILITY=1"
  set "ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE=1"
  set "ENDFIELD_RECOVERED_LINEAR_UNORM_FINAL_TARGET=1"
  set "ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT=1"
  set "ENDFIELD_CHARACTER_RECOVERY_INITIAL_MODEL=Endminf"
  echo Opening Endminf visual reproduction with explicitly approximate compatibility layers.
  "%UNITY_EXE%" -projectPath "%PROJECT_DIR%" -force-d3d12 -executeMethod EndfieldGraphShaderLabEditor.EndfieldEndminfOverviewEffectBindingBuilder.OpenVisualReproductionInPlayMode
  exit /b %ERRORLEVEL%
)

"%UNITY_EXE%" -projectPath "%PROJECT_DIR%"
