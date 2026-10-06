@echo off
setlocal
set "SWC_WORKSPACE=%LOCALAPPDATA%\SolidWorksCodex\Workspace"
if not exist "%SWC_WORKSPACE%" mkdir "%SWC_WORKSPACE%"
start "" explorer.exe "%SWC_WORKSPACE%"
