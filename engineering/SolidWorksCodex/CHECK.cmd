@echo off
setlocal
cd /d "%~dp0"
echo SolidWorks local connector check.
echo Start ONE SOLIDWORKS 2026 instance and open a small test part first.
echo Run Codex and SOLIDWORKS as the same user, normally WITHOUT elevation.
echo.
if not exist "SolidWorksLocal.exe" (
  call BUILD.cmd
  if errorlevel 1 goto failed
)
SolidWorksLocal.exe --self-test
if errorlevel 1 goto failed
SolidWorksLocal.exe --check
set "SW_CHECK_RESULT=%errorlevel%"
echo.
echo Check report: Reports\check_*.json
echo CHECK does not change or save SOLIDWORKS documents.
echo Write tools work only in %%LOCALAPPDATA%%\SolidWorksCodex\Workspace.
pause
exit /b %SW_CHECK_RESULT%
:failed
echo ERROR: Please copy or photograph this window.
pause
exit /b 2
