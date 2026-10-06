@echo off
setlocal
cd /d "%~dp0"
if not exist Reports mkdir Reports
explorer.exe "%~dp0Reports"

