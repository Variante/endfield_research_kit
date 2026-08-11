@echo off
rem Local path defaults used by the root WebUI wrapper scripts.
rem Edit this file once instead of passing path overrides to every command.
rem Command-line flags such as --game-root and --previous-export-root still win.

rem Installed Endfield_Data directory.
set "ENDFIELD_GAME_ROOT=D:\Program Files\Endfield Game\Endfield_Data"

rem Saved previous game-data export used by build_updates.bat.
set "ENDFIELD_PREVIOUS_EXPORT_ROOT=export_full_1d4"

rem Current game-data export used by build_updates.bat.
set "ENDFIELD_EXPORT_ROOT=export_full"
