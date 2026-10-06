@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0OPEN_WORKSPACE_DOC_CAPTURE.ps1"
