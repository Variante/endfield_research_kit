@echo off
rem Thin wrapper: export_assets.bat is export.bat --assets-only.
rem
rem Every option, the freshness check, and the benchmark report live in
rem export.bat so the two entry points cannot drift apart.
rem
rem   export_assets.bat              reuse the decoded assets already on disk
rem   export_assets.bat --from-game  decode assets and CN audio from the game
rem   export_assets.bat --help       all options
call "%~dp0export.bat" --assets-only %*
exit /b %errorlevel%
