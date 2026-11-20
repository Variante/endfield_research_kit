@echo off
rem Local path defaults used by the root WebUI wrapper scripts.
rem Edit this file once instead of passing path overrides to every command.
rem Existing environment variables and explicit command-line path flags win.

rem Installed Endfield_Data directory.
if not defined ENDFIELD_GAME_ROOT set "ENDFIELD_GAME_ROOT=D:\Program Files\Endfield Game\Endfield_Data"

rem Saved previous game-data export used by build_updates.bat.
if not defined ENDFIELD_PREVIOUS_EXPORT_ROOT set "ENDFIELD_PREVIOUS_EXPORT_ROOT=export_full_1d5d3"

rem Current game-data export used by build_updates.bat.
if not defined ENDFIELD_EXPORT_ROOT set "ENDFIELD_EXPORT_ROOT=export_full"
