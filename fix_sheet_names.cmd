@echo off
REM Run this straight after exporting zulu_a7.sch from Fusion.
REM Fusion's .sch export drops the sheet-name attribute the browser
REM labels sheets from; this puts it back. Safe to run any number of
REM times - it does nothing if the names are already there.
cd /d "%~dp0"
python tools\restore_sheet_names.py
echo.
pause
