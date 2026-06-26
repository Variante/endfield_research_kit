@echo off
setlocal EnableExtensions

set "DEFAULT_GAME_ROOT=D:\Program Files\Endfield Game\Endfield_Data"

if exist "%~dp0endfield_paths.bat" call "%~dp0endfield_paths.bat"
if errorlevel 1 exit /b %errorlevel%

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="/h" goto :help
if /I "%~1"=="help" goto :help

set "GAME_ROOT="
set "SERVE_WEBUI=1"

:parse_args
if "%~1"=="" goto :parsed_args
if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="/h" goto :help
if /I "%~1"=="help" goto :help
set "ARG=%~1"
set "NEXT_ARG=%~2"
if /I "%ARG:~0,12%"=="--game-root=" (
  if "%ARG:~12%"=="" (
    echo Missing value for --game-root.
    exit /b 2
  )
  set "GAME_ROOT=%ARG:~12%"
  shift
  goto :parse_args
)
if /I "%ARG%"=="--game-root" (
  if "%~2"=="" (
    echo Missing value for --game-root.
    exit /b 2
  )
  if "%NEXT_ARG:~0,2%"=="--" (
    echo Missing value for --game-root.
    exit /b 2
  )
  set "GAME_ROOT=%NEXT_ARG%"
  shift
  shift
  goto :parse_args
)
if /I "%ARG%"=="--no-serve" (
  set "SERVE_WEBUI=0"
  shift
  goto :parse_args
)
if /I "%ARG%"=="--skip-assets" (
  echo [setup] --skip-assets is no longer needed; setup now skips optional assets and Updates by default.
  shift
  goto :parse_args
)

echo Unknown option: %ARG%
echo Run setup_first_time.bat --help for usage.
exit /b 2

:parsed_args
pushd "%~dp0" || exit /b 1

if not defined GAME_ROOT if not "%ENDFIELD_GAME_ROOT%"=="" set "GAME_ROOT=%ENDFIELD_GAME_ROOT%"
if not defined GAME_ROOT set "GAME_ROOT=%DEFAULT_GAME_ROOT%"


set "ANIMESTUDIO_EXE=%CD%\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe"

echo [setup] Endfield_Data: "%GAME_ROOT%"
if not exist "%GAME_ROOT%\" (
  echo [setup] Endfield_Data was not found.
  echo [setup] Edit endfield_paths.bat, pass --game-root "...\Endfield_Data", or set ENDFIELD_GAME_ROOT.
  popd
  exit /b 1
)

echo.
echo [setup 1/6] Checking required commands...
call :require_command git "Install Git, then rerun this script."
if errorlevel 1 goto :failed
call :require_command python "Install Python 3 and make sure python is on PATH."
if errorlevel 1 goto :failed
call :require_command powershell.exe "PowerShell is required to check and reuse the WebUI server."
if errorlevel 1 goto :failed
python --version
if errorlevel 1 goto :failed

echo.
echo [setup 2/6] Initializing the AnimeStudio submodule...
git submodule update --init tools/AnimeStudio
if errorlevel 1 goto :failed

echo.
echo [setup 3/6] Building the AnimeStudio CLI...
call .\scripts\animestudio\setup_dotnet9.bat
if errorlevel 1 goto :failed
call .\scripts\animestudio\rebuild.bat -Target CLI
if errorlevel 1 goto :failed
if not exist "%ANIMESTUDIO_EXE%" (
  echo [setup] Expected AnimeStudio CLI was not found:
  echo [setup]   %ANIMESTUDIO_EXE%
  goto :failed
)

echo.
echo [setup 4/6] Verifying AnimeStudio VFS commands...
call :check_animestudio_vfs_help dump
if errorlevel 1 goto :failed
call :check_animestudio_vfs_help audio
if errorlevel 1 goto :failed
call :check_animestudio_vfs_help vfs-index
if errorlevel 1 goto :failed
call :check_animestudio_vfs_help list
if errorlevel 1 goto :failed

echo.
echo [setup 5/6] Exporting Story and Text Tables data from the installed game...
call .\export.bat --export-from-game --game-root "%GAME_ROOT%"
if errorlevel 1 goto :failed

echo.
echo [setup 6/6] Optional follow-up steps for a fuller WebUI experience...
echo [setup] Asset media and CN audio export is optional and can take several hours.
echo [setup] Run this later when you want Assets tab media and playable CN audio:
echo [setup]   .\export_assets.bat --export-from-game
echo [setup] Updates tracking is optional until you want the Updates tab baseline/feed.
echo [setup] Initialize a first-time empty baseline with:
echo [setup]   .\build_updates.bat --init-build

echo.
echo [setup] First-time setup finished.
echo [setup] WebUI URL: http://127.0.0.1:8765/

if "%SERVE_WEBUI%"=="1" (
  call :serve_webui
  if errorlevel 1 goto :failed
) else (
  echo [setup] Run python serve.py when you are ready to browse the WebUI.
)

popd
exit /b 0

:require_command
where %~1 >nul 2>nul
if errorlevel 1 (
  echo [setup] Missing required command: %~1
  echo [setup] %~2
  exit /b 1
)
exit /b 0

:check_animestudio_vfs_help
set "HELP_FILE=%TEMP%\animestudio-vfs-%~1-%RANDOM%.txt"
"%ANIMESTUDIO_EXE%" %~1 --help > "%HELP_FILE%" 2>&1
if errorlevel 1 (
  type "%HELP_FILE%"
  del "%HELP_FILE%" >nul 2>nul
  echo [setup] AnimeStudio %~1 --help failed.
  exit /b 1
)
if /I "%~1"=="list" goto :check_animestudio_vfs_help_done
findstr /C:"--fallback-assets" "%HELP_FILE%" >nul
if errorlevel 1 (
  type "%HELP_FILE%"
  del "%HELP_FILE%" >nul 2>nul
  echo [setup] AnimeStudio %~1 is missing --fallback-assets.
  echo [setup] Rebuild the AnimeStudio CLI from this checkout.
  exit /b 1
)
:check_animestudio_vfs_help_done
del "%HELP_FILE%" >nul 2>nul
exit /b 0

:serve_webui
echo.
echo [setup] Checking whether http://127.0.0.1:8765/ is already running...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:8765/' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if not errorlevel 1 (
  echo [setup] Reusing the existing WebUI server at http://127.0.0.1:8765/
  exit /b 0
)
echo [setup] Starting the WebUI server. Keep this window open while browsing.
python serve.py
exit /b %errorlevel%

:failed
echo.
echo [setup] Setup failed. Fix the message above, then rerun setup_first_time.bat.
popd
exit /b 1

:help
echo Usage: setup_first_time.bat [--game-root PATH] [--no-serve]
echo.
echo Runs the full first-time WebUI setup from an installed Endfield client:
echo   1. check Git, Python, and PowerShell
echo   2. initialize tools\AnimeStudio
echo   3. build the AnimeStudio CLI
echo   4. verify AnimeStudio VFS/audio commands
echo   5. run export.bat --export-from-game
echo   6. print optional export_assets/build_updates follow-up commands
echo   7. start python serve.py, unless a default server is already running
echo.
echo Options:
echo   --game-root PATH        Installed Endfield_Data folder. Defaults to
echo                           endfield_paths.bat / ENDFIELD_GAME_ROOT, then:
echo                           %DEFAULT_GAME_ROOT%
echo   --no-serve             Build Story/Text Tables, but do not start the WebUI server.
echo   --help                 Show this help text.
echo.
echo Examples:
echo   notepad endfield_paths.bat
echo   setup_first_time.bat
echo   setup_first_time.bat --game-root "E:\Games\Endfield Game\Endfield_Data"
echo   setup_first_time.bat --game-root "E:\Games\Endfield Game\Endfield_Data" --no-serve
echo.
endlocal
exit /b 0
