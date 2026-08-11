@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "REPO_ROOT=%PROJECT_DIR%.."
call "%REPO_ROOT%\endfield_paths.bat"
if errorlevel 1 exit /b %errorlevel%

set "CLI=%REPO_ROOT%\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe"
set "DUMMY_DLLS=%REPO_ROOT%\tools\DummyDll"
set "WORK_ROOT=%REPO_ROOT%\scratch\charinfo_playable_profiles"
set "GAME_STREAMING=%ENDFIELD_GAME_ROOT%\StreamingAssets"
set "GAME_PERSISTENT=%ENDFIELD_GAME_ROOT%\Persistent"

if not exist "%CLI%" (
  echo AnimeStudio CLI is missing: %CLI%
  exit /b 1
)
if not exist "%GAME_STREAMING%" (
  echo Installed StreamingAssets is missing: %GAME_STREAMING%
  exit /b 1
)
if not exist "%GAME_PERSISTENT%" (
  echo Installed Persistent assets are missing: %GAME_PERSISTENT%
  exit /b 1
)

pushd "%REPO_ROOT%"
python "%PROJECT_DIR%tools\recover_playable_charinfo_profiles.py" prepare-display-config
if errorlevel 1 goto :fail

set "ANIMESTUDIO_EXPORT_JSON_RAW=1"
"%CLI%" "%GAME_STREAMING%" "%WORK_ROOT%\display_config_json" ^
  --game ArknightsEndfield ^
  --logger_flags Warning Error ^
  --group_assets ByType ^
  --map_op Load ^
  --export_type JSON ^
  --types MonoBehaviour:Both ^
  --dummy_dlls "%DUMMY_DLLS%" ^
  --filter_data "%WORK_ROOT%\display_config_filter.json"
if errorlevel 1 goto :fail
set "ANIMESTUDIO_EXPORT_JSON_RAW="

python "%PROJECT_DIR%tools\recover_playable_charinfo_profiles.py" prepare
if errorlevel 1 goto :fail

"%CLI%" "%GAME_STREAMING%" "%WORK_ROOT%\dependencies_json" ^
  --game ArknightsEndfield ^
  --logger_flags Warning Error ^
  --group_assets ByType ^
  --map_op Load ^
  --export_type JSON ^
  --types GameObject:Both Transform:Both MonoBehaviour:Both Light:Both ^
  --dummy_dlls "%DUMMY_DLLS%" ^
  --filter_data "%WORK_ROOT%\camera_light_filter_streamingassets.json"
if errorlevel 1 goto :fail

"%CLI%" "%GAME_PERSISTENT%" "%WORK_ROOT%\dependencies_json" ^
  --game ArknightsEndfield ^
  --logger_flags Warning Error ^
  --group_assets ByType ^
  --map_op Load ^
  --export_type JSON ^
  --types GameObject:Both Transform:Both MonoBehaviour:Both Light:Both ^
  --dummy_dlls "%DUMMY_DLLS%" ^
  --filter_data "%WORK_ROOT%\camera_light_filter_persistent.json"
if errorlevel 1 goto :fail

"%CLI%" "%GAME_STREAMING%" "%WORK_ROOT%\sprites_json" ^
  --game ArknightsEndfield ^
  --logger_flags Warning Error ^
  --group_assets ByType ^
  --map_op Load ^
  --export_type JSON ^
  --types Sprite:Both Texture2D:Parse ^
  --filter_data "%WORK_ROOT%\portrait_sprite_filter_streamingassets.json"
if errorlevel 1 goto :fail

"%CLI%" "%GAME_PERSISTENT%" "%WORK_ROOT%\sprites_json" ^
  --game ArknightsEndfield ^
  --logger_flags Warning Error ^
  --group_assets ByType ^
  --map_op Load ^
  --export_type JSON ^
  --types Sprite:Both Texture2D:Parse ^
  --filter_data "%WORK_ROOT%\portrait_sprite_filter_persistent.json"
if errorlevel 1 goto :fail

python "%PROJECT_DIR%tools\recover_playable_charinfo_profiles.py" extract
if errorlevel 1 goto :fail
python "%PROJECT_DIR%tools\extract_original_render_parameters.py"
if errorlevel 1 goto :fail
python "%PROJECT_DIR%tools\extract_original_operator_lights.py"
if errorlevel 1 goto :fail
popd
echo Recovered all playable CharInfo camera, portrait, volume, and light profiles.
exit /b 0

:fail
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
