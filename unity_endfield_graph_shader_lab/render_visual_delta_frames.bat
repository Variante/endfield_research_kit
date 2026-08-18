@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Render a comparison frame and measure it against the original game capture.
rem
rem   --baseline   the maintained default path: every recovered selector that
rem                has a serialized scene companion is explicitly forced off, so
rem                the frame does not inherit state saved by an earlier
rem                diagnostic run.
rem   --composed   the validated recovered chain enabled together in one frame.
rem                Capture/audit-only probes are deliberately excluded; they
rem                write evidence rather than contribute shading.

set "PROJECT_DIR=%~dp0"
set "PROJECT_PATH=%PROJECT_DIR:~0,-1%"
set "UNITY_EXE=D:\Program Files\2022.3.62f3\Editor\Unity.exe"
set "OUTPUT_ROOT=%PROJECT_PATH%\scratch\character_recovery\visual_delta"

set "PROFILE="
set "NO_READY_SUBSET="
set "CHARACTER=both"
set "API=d3d12"

:PARSE
if "%~1"=="" goto PARSED
if /i "%~1"=="--baseline" ( set "PROFILE=baseline" & shift & goto PARSE )
if /i "%~1"=="--composed" ( set "PROFILE=composed" & shift & goto PARSE )
if /i "%~1"=="--no-ready-subset" ( set "NO_READY_SUBSET=1" & shift & goto PARSE )
if /i "%~1"=="--character" ( set "CHARACTER=%~2" & shift & shift & goto PARSE )
if /i "%~1"=="--d3d11" ( set "API=d3d11" & shift & goto PARSE )
if /i "%~1"=="--d3d12" ( set "API=d3d12" & shift & goto PARSE )
if /i "%~1"=="--help" goto USAGE
echo Unknown option: %~1
goto USAGE

:PARSED
if not exist "%UNITY_EXE%" (
  echo Unity editor not found: %UNITY_EXE%
  exit /b 1
)
if "%PROFILE%"=="" (
  echo Select --baseline or --composed.
  goto USAGE
)
if not exist "%OUTPUT_ROOT%" mkdir "%OUTPUT_ROOT%"

set "LABEL=%PROFILE%"
if /i "%PROFILE%"=="composed" if "%NO_READY_SUBSET%"=="1" set "LABEL=composed_no_ready_subset"

rem Selectors with a serialized scene companion are tri-state, so the baseline
rem states its zeros explicitly instead of relying on an unset variable.
set "ENDFIELD_RECOVERED_CHARINFO_PRESENTATION=0"
set "ENDFIELD_RECOVERED_CHARINFO_READY_SUBSET_DIAGNOSTIC=0"
set "ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT=0"
set "ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_MODE=off"

if /i "%PROFILE%"=="composed" (
  rem Character response and post semantics shared by every validated run.
  set "ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE=1"
  set "ENDFIELD_RECOVERED_EYE_RESPONSE_SEMANTICS=1"
  set "ENDFIELD_RECOVERED_FACE_HIGHLIGHT_SEMANTICS=1"
  set "ENDFIELD_RECOVERED_POST_SEMANTICS=1"

  rem Light scheduling and the punctual/character shadow chain.
  set "ENDFIELD_RECOVERED_CLUSTERED_NPR_LIGHT_LOOP=1"
  set "ENDFIELD_RECOVERED_LIGHT_BINNING_MEMBERSHIP=1"
  set "ENDFIELD_RECOVERED_CANONICAL_BINNING_BUFFER=1"
  set "ENDFIELD_RECOVERED_ISOLATED_PUNCTUAL_SOFT_SHADOWS=1"
  set "ENDFIELD_RECOVERED_PUNCTUAL_SHADOW_TILE_RESOLUTION=1024"
  set "ENDFIELD_RECOVERED_SEPARATE_CHARACTER_SHADOW=1"
  set "ENDFIELD_RECOVERED_VISIBILITY_SH=1"

  rem Deferred frame data recovered and validated bit-exact in isolation.
  set "ENDFIELD_RECOVERED_DEFERRED_TRANSFORM_VARIABLES=1"
  set "ENDFIELD_RECOVERED_DEFERRED_LIGHT_DATA=1"
  set "ENDFIELD_RECOVERED_DEFERRED_SHADOW_DATA=1"
  set "ENDFIELD_RECOVERED_SHADER_VARIABLES_GLOBAL=1"
  set "ENDFIELD_RECOVERED_DEFERRED_GBUFFER_FRAME=1"

  rem The executed Forward consumer of the recovered screen-shadow mask.
  set "ENDFIELD_RECOVERED_SCREEN_SHADOW_MASK_CONSUMER_DIAGNOSTIC=1"

  rem The CharInfo presentation subset the deferred frame runs against. It
  rem swaps the compatibility backdrop for a partial source subset with no
  rem SphereOutside or ShadowPlane, so it is separable from character shading.
  if not "%NO_READY_SUBSET%"=="1" set "ENDFIELD_RECOVERED_CHARINFO_READY_SUBSET_DIAGNOSTIC=1"
)

if /i "%CHARACTER%"=="both" (
  call :RUN wulfa
  if not "!ERRORLEVEL!"=="0" exit /b !ERRORLEVEL!
  call :RUN zhuangfy
  exit /b !ERRORLEVEL!
)
call :RUN %CHARACTER%
exit /b %ERRORLEVEL%

:RUN
set "NAME=%~1"
if /i "%NAME%"=="wulfa" ( set "METHOD=RenderRuntimeReferenceWulfaPreview" ) else (
  if /i "%NAME%"=="zhuangfy" ( set "METHOD=RenderRuntimeReferenceZhuangfyPreview" ) else (
    echo Unknown character: %NAME%
    exit /b 2
  )
)
set "LOG_PATH=%OUTPUT_ROOT%\%LABEL%_%NAME%.log"
set "FRAME_PATH=%OUTPUT_ROOT%\%NAME%_%LABEL%.png"

echo Rendering %NAME% [%LABEL%] with %API%...
"%UNITY_EXE%" -batchmode -quit -projectPath "%PROJECT_PATH%" -force-%API% -executeMethod EndfieldGraphShaderLabEditor.EndfieldManifestCharacterSetup.%METHOD% -logFile "%LOG_PATH%"
set "UNITY_EXIT=%ERRORLEVEL%"
if not "%UNITY_EXIT%"=="0" (
  echo Unity render failed for %NAME% [%LABEL%]: exit %UNITY_EXIT%
  exit /b %UNITY_EXIT%
)
copy /y "%PROJECT_PATH%\..\scratch\runtime_reference_%NAME%.png" "%FRAME_PATH%" >nul
if not "%ERRORLEVEL%"=="0" exit /b %ERRORLEVEL%

python "%PROJECT_PATH%\tools\compare_recovered_vs_original.py" --character %NAME% --recovered "%FRAME_PATH%" --label %LABEL% --report-root "%OUTPUT_ROOT%"
exit /b %ERRORLEVEL%

:USAGE
echo Usage: %~nx0 --baseline ^| --composed [--no-ready-subset] [--character wulfa^|zhuangfy^|both] [--d3d11^|--d3d12]
exit /b 2
