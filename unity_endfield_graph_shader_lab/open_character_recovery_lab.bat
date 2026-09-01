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
  set "ENDFIELD_ENDMINF_VISUAL_COMPATIBILITY_PREROLL_SECONDS=0"
  rem Exact serialized post curves consume the authenticated FromOveview
  rem AnimatorStateInfo clock; this does not enable broad visual compatibility.
  if not defined ENDFIELD_RECOVERED_ENDMINF_SOURCE_POST set "ENDFIELD_RECOVERED_ENDMINF_SOURCE_POST=1"
  rem Retain the ten source-identified M01/M38 fly-in rock owners. Exact M27
  rem replaces only the hand-crystal row and does not replace these owners.
  set "ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT=1"
  rem Keep the source-owned GridDeco/Far and ShadowPlane separate from the
  rem fitted neutral plate and generic ready-subset diagnostics.
  set "ENDFIELD_ENDMINF_SOURCE_BACKGROUND=1"
  set "ENDFIELD_ENDMINF_BACKDROP_VISUAL_COMPATIBILITY=0"
  set "ENDFIELD_RECOVERED_CHARINFO_READY_SUBSET_DIAGNOSTIC=0"
  set "ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE=1"
  set "ENDFIELD_RECOVERED_VISIBILITY_SH=1"
  set "ENDFIELD_RECOVERED_LINEAR_UNORM_FINAL_TARGET=1"
  set "ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT=1"
  rem Deferred/SphereOutside remains a default-off diagnostic. Its current
  rem screen-shadow prerequisite is content-invalid and vertically masks the
  rem portrait, so the maintained visual path does not request that chain.
  rem Captured opening-strip, M13, and M21 packets remain opt-in ABI probes.
  rem They are not maintained presentation: replaying one or a few observed
  rem particle states substitutes fixed geometry for the source runtime that
  rem generates the authored motion, placement, and material evolution.
  rem M31 stays diagnostic-only until a corrected observer capture closes the
  rem live SceneColor chronology; its current replay validates transport but
  rem mildly regresses the aligned reference comparison.
  rem The exact Uber packet remains an explicit diagnostic. Its native draw is
  rem validated, but the captured SceneColor/input chronology is not yet closed
  rem and the current replay regresses every aligned effect sample versus off.
  rem Reproduce UIGyroscopeEffect from the current live cursor through its
  rem recovered screen normalization, curves, PreLate change edge, and OutQuad.
  set "ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_MODE=live-input"
  set "ENDFIELD_CHARACTER_RECOVERY_INITIAL_MODEL=Endminf"
  echo Opening Endminf reproduction with authored effect timelines and source-backed presentation.
  "%UNITY_EXE%" -projectPath "%PROJECT_PATH%" -force-d3d11 -executeMethod EndfieldGraphShaderLabEditor.EndfieldEndminfOverviewEffectBindingBuilder.OpenVisualReproductionInPlayMode
  exit /b %ERRORLEVEL%

:open_lab
"%UNITY_EXE%" -projectPath "%PROJECT_PATH%" -force-d3d11
