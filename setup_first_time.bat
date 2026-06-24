@echo off
setlocal EnableExtensions

set "DEFAULT_GAME_ROOT=D:\Program Files\Endfield Game\Endfield_Data"
set "FLUFFY_URL=https://drive.google.com/file/d/1WqShlYyM_QpEqzM_myRkdpTGifYOuVHg/view?usp=sharing"

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="/h" goto :help
if /I "%~1"=="help" goto :help

set "GAME_ROOT="
set "SERVE_WEBUI=1"
set "SKIP_ASSETS=0"
set "REFRESH_FLUFFY_SRC=0"

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
  set "SKIP_ASSETS=1"
  shift
  goto :parse_args
)
if /I "%ARG%"=="--refresh-fluffy-src" (
  set "REFRESH_FLUFFY_SRC=1"
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

set "FLUFFY_ZIP=%CD%\fluffy-dumper.zip"
set "FLUFFY_SRC=%CD%\tools\fluffy-dumper-src"
set "FLUFFY_EXE=%FLUFFY_SRC%\target\release\fluffy-dumper.exe"
set "ANIMESTUDIO_EXE=%CD%\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe"

echo [setup] Endfield_Data: "%GAME_ROOT%"
if not exist "%GAME_ROOT%\" (
  echo [setup] Endfield_Data was not found.
  echo [setup] Pass --game-root "...\Endfield_Data" or set ENDFIELD_GAME_ROOT.
  popd
  exit /b 1
)

echo.
echo [setup 1/7] Checking required commands...
call :require_command git "Install Git, then rerun this script."
if errorlevel 1 goto :failed
call :require_command python "Install Python 3 and make sure python is on PATH."
if errorlevel 1 goto :failed
call :require_command powershell.exe "PowerShell is required to download and unpack fluffy-dumper."
if errorlevel 1 goto :failed
call :require_command cargo "Install Rust from https://rustup.rs/, then rerun this script."
if errorlevel 1 goto :failed
python --version
if errorlevel 1 goto :failed
cargo --version
if errorlevel 1 goto :failed

echo.
echo [setup 2/7] Initializing the AnimeStudio submodule...
git submodule update --init tools/AnimeStudio
if errorlevel 1 goto :failed

echo.
echo [setup 3/7] Building the AnimeStudio CLI...
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
echo [setup 4/7] Preparing fluffy-dumper...
if "%REFRESH_FLUFFY_SRC%"=="1" goto :download_fluffy
if exist "%FLUFFY_SRC%\Cargo.toml" (
  echo [setup] Reusing existing source at tools\fluffy-dumper-src.
  goto :build_fluffy
)

:download_fluffy
echo [setup] Downloading %FLUFFY_URL%
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $url='%FLUFFY_URL%'; if ($url -match 'drive\.google\.com/file/d/([^/]+)/') { $url = 'https://drive.google.com/uc?export=download&id=' + $Matches[1] }; New-Item -ItemType Directory -Force -Path '%CD%\tools' | Out-Null; Invoke-WebRequest -Uri $url -OutFile '%FLUFFY_ZIP%'; New-Item -ItemType Directory -Force -Path '%FLUFFY_SRC%' | Out-Null; Expand-Archive -Force -LiteralPath '%FLUFFY_ZIP%' -DestinationPath '%FLUFFY_SRC%'"
if errorlevel 1 goto :failed
if not exist "%FLUFFY_SRC%\Cargo.toml" (
  echo [setup] The fluffy-dumper source zip did not unpack to:
  echo [setup]   %FLUFFY_SRC%\Cargo.toml
  goto :failed
)

:build_fluffy
cargo build --release --manifest-path "%FLUFFY_SRC%\Cargo.toml"
if errorlevel 1 goto :failed
if not exist "%FLUFFY_EXE%" (
  echo [setup] Expected fluffy-dumper executable was not found:
  echo [setup]   %FLUFFY_EXE%
  goto :failed
)
call :check_fluffy_help dump
if errorlevel 1 goto :failed
call :check_fluffy_help audio
if errorlevel 1 goto :failed

echo.
echo [setup 5/7] Exporting Story and Reference data from the installed game...
call .\export.bat --export-from-game --game-root "%GAME_ROOT%"
if errorlevel 1 goto :failed

if "%SKIP_ASSETS%"=="1" (
  echo.
  echo [setup 6/7] Skipping asset and CN audio export because --skip-assets was passed.
) else (
  echo.
  echo [setup 6/7] Exporting Assets tab media and CN audio from the installed game...
  call .\export_assets.bat --export-from-game --game-root "%GAME_ROOT%"
  if errorlevel 1 goto :failed
)

echo.
echo [setup 7/7] Creating the initial Updates baseline...
call .\build_updates.bat --init-build
if errorlevel 1 goto :failed

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

:check_fluffy_help
set "HELP_FILE=%TEMP%\fluffy-dumper-%~1-%RANDOM%.txt"
"%FLUFFY_EXE%" %~1 --help > "%HELP_FILE%" 2>&1
if errorlevel 1 (
  type "%HELP_FILE%"
  del "%HELP_FILE%" >nul 2>nul
  echo [setup] fluffy-dumper %~1 --help failed.
  exit /b 1
)
findstr /C:"--fallback-assets" "%HELP_FILE%" >nul
if errorlevel 1 (
  type "%HELP_FILE%"
  del "%HELP_FILE%" >nul 2>nul
  echo [setup] fluffy-dumper %~1 is missing --fallback-assets.
  echo [setup] Rebuild from this project's patched source zip.
  exit /b 1
)
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
echo Usage: setup_first_time.bat [--game-root PATH] [--no-serve] [--skip-assets] [--refresh-fluffy-src]
echo.
echo Runs the full first-time WebUI setup from an installed Endfield client:
echo   1. check Git, Python, PowerShell, and Rust/Cargo
echo   2. initialize tools\AnimeStudio
echo   3. build the AnimeStudio CLI
echo   4. download, build, and verify the patched fluffy-dumper
echo   5. run export.bat --export-from-game
echo   6. run export_assets.bat --export-from-game
echo   7. run build_updates.bat --init-build
echo   8. start python serve.py, unless a default server is already running
echo.
echo Options:
echo   --game-root PATH        Installed Endfield_Data folder. Defaults to
echo                           ENDFIELD_GAME_ROOT, then:
echo                           %DEFAULT_GAME_ROOT%
echo   --no-serve             Build everything, but do not start the WebUI server.
echo   --skip-assets          Skip the heavier Assets tab media and CN audio export.
echo   --refresh-fluffy-src   Download and overlay the patched fluffy-dumper source.
echo   --help                 Show this help text.
echo.
echo Examples:
echo   setup_first_time.bat
echo   setup_first_time.bat --game-root "E:\Games\Endfield Game\Endfield_Data"
echo   setup_first_time.bat --game-root "E:\Games\Endfield Game\Endfield_Data" --no-serve
echo.
endlocal
exit /b 0
