@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0CREATE_TEST_PROFILE_TUBES_2_4.ps1"
echo.
echo Report: %~dp0_profile_tubes_2_4_live_report.txt
pause
