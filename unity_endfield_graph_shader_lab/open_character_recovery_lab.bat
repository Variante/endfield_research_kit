@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "PROJECT_PATH=%PROJECT_DIR:~0,-1%"
set "UNITY_EXE=D:\Program Files\2022.3.62f3\Editor\Unity.exe"

if not exist "%UNITY_EXE%" (
  echo Unity 2022.3.62f3 not found at "%UNITY_EXE%".
  exit /b 1
)

if /i "%~1"=="--lab" goto open_lab
if "%~1"=="" goto open_endminf
if /i "%~1"=="--endminf-reproduction" goto open_endminf

echo Unknown option: %~1
echo Use no option for the Endminf reference reproduction, or --lab for the general viewer.
exit /b 2

:open_endminf
  set "ENDFIELD_ENDMINF_VISUAL_COMPATIBILITY=1"
  rem Direct UI-free registration places the maintained Aug-24 no-frame-generation post pulse on the authored body clock.
  set "ENDFIELD_ENDMINF_VISUAL_COMPATIBILITY_PREROLL_SECONDS=0"
  rem Retain the ten source-identified M01/M38 fly-in rocks. Exact M27 mode
  rem redirects only its own hand-crystal row and does not replace these owners.
  set "ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT=1"
  set "ENDFIELD_ENDMINF_BACKDROP_VISUAL_COMPATIBILITY=1"
  set "ENDFIELD_RECOVERED_CHARINFO_READY_SUBSET_DIAGNOSTIC=1"
  set "ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE=1"
  set "ENDFIELD_RECOVERED_VISIBILITY_SH=1"
  set "ENDFIELD_RECOVERED_LINEAR_UNORM_FINAL_TARGET=1"
  set "ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT=1"
  rem Source-closed SphereOutside + exact Default Lit resolve, presented before ForwardOpaque.
  set "ENDFIELD_RECOVERED_DEFERRED_GBUFFER_FRAME=1"
  set "ENDFIELD_RECOVERED_SPHERE_OUTSIDE_PRESENTATION=1"
  set "ENDFIELD_RECOVERED_DEFERRED_EXACT_CONSUMER=1"
  rem Exact temporal VFX owners improve the no-frame-generation UI-free sequence.
  set "ENDFIELD_RECOVERED_ENDMINF_M13_EXACT=1"
  set "ENDFIELD_RECOVERED_ENDMINF_M14_EXACT=1"
  set "ENDFIELD_RECOVERED_ENDMINF_M27_HGBUFFER=1"
  set "ENDFIELD_RECOVERED_ENDMINF_M27_EXACT_DXBC=1"
  set "ENDFIELD_RECOVERED_ENDMINF_M27_PRESENTATION=1"
  set "ENDFIELD_RECOVERED_CANONICAL_BINNING_BUFFER=1"
  set "ENDFIELD_RECOVERED_SEPARATE_CHARACTER_SHADOW=1"
  set "ENDFIELD_RECOVERED_LOW_RES_DIRECTIONAL_SHADOW=1"
  set "ENDFIELD_RECOVERED_SCREEN_SHADOW_R_ATTACHMENT_DIAGNOSTIC=1"
  rem Recording-specific live cursor endpoint measured from the canonical clean
  rem videos/2026-08-26_21-25-50.mkv reference at source pixel (1036,75).
  set "ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_MODE=recorded-input"
  set "ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_INPUT_X=-0.4604167"
  set "ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_INPUT_Y=0.9305556"
  set "ENDFIELD_CHARACTER_RECOVERY_INITIAL_MODEL=Endminf"
  echo Opening Endminf reproduction with physical SphereOutside and exact M13/M14/M27 presentation.
  "%UNITY_EXE%" -projectPath "%PROJECT_PATH%" -force-d3d11 -executeMethod EndfieldGraphShaderLabEditor.EndfieldEndminfOverviewEffectBindingBuilder.OpenVisualReproductionInPlayMode
  exit /b %ERRORLEVEL%

:open_lab
"%UNITY_EXE%" -projectPath "%PROJECT_PATH%" -force-d3d11
