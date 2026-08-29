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
  rem Deferred/SphereOutside remains a default-off diagnostic. Its current
  rem screen-shadow prerequisite is content-invalid and vertically masks the
  rem portrait, so the maintained visual path does not request that chain.
  rem Use the four exact retained opening-strip packets only at their certified
  rem phases. Their source geometry/shaders/resources and native submission are
  rem closed; retail temporal accumulation remains a separate visible gap.
  set "ENDFIELD_RECOVERED_ENDMINF_OPENING_STRIP_EXACT=1"
  rem Corrected M13 packets 1/2 improve the aligned peak shell. Packet 0 is
  rem rejected by the runtime; M14 and M20 remain transport diagnostics.
  set "ENDFIELD_RECOVERED_ENDMINF_M13_EXACT=1"
  rem Frame 2775 closes the complete draw-local M21 stone-shell packet. It is
  rem admitted only at its certified 4.5000 s sample and restores the authored
  rem ParticleSystem on adjacent ticks, so this does not repeat a static packet
  rem across the burst or replace the separately textured M01/M38 stones.
  set "ENDFIELD_RECOVERED_ENDMINF_M21_PEAK_EXACT=1"
  rem M31 stays diagnostic-only until a corrected observer capture closes the
  rem live SceneColor chronology; its current replay validates transport but
  rem mildly regresses the aligned reference comparison.
  set "ENDFIELD_RECOVERED_ENDMINF_UBER_EXACT=1"
  rem Recording-specific live cursor endpoint measured from the canonical clean
  rem videos/2026-08-26_21-25-50.mkv reference at source pixel (1036,75).
  set "ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_MODE=recorded-input"
  set "ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_INPUT_X=-0.4604167"
  set "ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_INPUT_Y=0.9305556"
  set "ENDFIELD_CHARACTER_RECOVERY_INITIAL_MODEL=Endminf"
  echo Opening Endminf reproduction with exact opening-strip and aligned M13/M21 peak presentation.
  "%UNITY_EXE%" -projectPath "%PROJECT_PATH%" -force-d3d11 -executeMethod EndfieldGraphShaderLabEditor.EndfieldEndminfOverviewEffectBindingBuilder.OpenVisualReproductionInPlayMode
  exit /b %ERRORLEVEL%

:open_lab
"%UNITY_EXE%" -projectPath "%PROJECT_PATH%" -force-d3d11
