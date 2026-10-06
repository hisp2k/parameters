@echo off
setlocal
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CREATE_TEST_POLYGON_CORNERS.ps1"
if errorlevel 1 (
  echo.
  echo TEST FAILED. Send a screenshot and the complete text from this window.
)
pause
