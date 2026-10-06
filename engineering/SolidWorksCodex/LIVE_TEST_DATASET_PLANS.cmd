@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0LIVE_TEST_DATASET_PLANS.ps1" > "%~dp0_claude_live_test_console.txt" 2>&1
