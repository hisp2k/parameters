@echo off
setlocal
cd /d "%~dp0"
echo PROFILE PARTS 2.5 LIVE TEST
echo Start exactly one SOLIDWORKS 2026 instance before continuing.
echo This creates only new uniquely named local Workspace parts.
echo Existing documents are not saved or edited.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0CREATE_TEST_PROFILE_PARTS_2_5.ps1"
set "exitCode=%ERRORLEVEL%"
echo.
type "%~dp0_profile_parts_2_5_live_report.txt" 2>nul
echo.
if not "%exitCode%"=="0" (
  echo TEST FAILED. Send the report shown above.
) else (
  echo TEST FINISHED. Inspect the three generated parts in SOLIDWORKS.
)
pause
exit /b %exitCode%
