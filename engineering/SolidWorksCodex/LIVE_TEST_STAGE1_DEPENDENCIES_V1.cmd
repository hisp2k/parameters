@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0LIVE_TEST_STAGE1_DEPENDENCIES_V1.ps1"
