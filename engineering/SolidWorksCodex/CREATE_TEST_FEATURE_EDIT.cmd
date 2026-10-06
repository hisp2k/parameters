@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0CREATE_TEST_FEATURE_EDIT.ps1"
if errorlevel 1 (
  echo.
  echo TEST FAILED. Send a screenshot and the complete text from this window.
  pause
)
