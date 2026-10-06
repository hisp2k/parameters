@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0CREATE_TEST_PROFILE_PART_REALPDF_CAPTURE.ps1"
