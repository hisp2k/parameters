@echo off
setlocal
cd /d "%~dp0"
set "SW_CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%SW_CSC%" (
  echo ERROR: Windows .NET Framework x64 C# compiler was not found.
  echo Use the provided SolidWorksLocal.exe. Do not install random DLLs.
  exit /b 2
)
if exist "SolidWorksLocal.exe" (
  echo Creating a backup of the existing connector before rebuilding...
  powershell.exe -NoProfile -Command "$p=Join-Path (Get-Location) 'SolidWorksLocal.exe'; Copy-Item -LiteralPath $p -Destination ($p+'.'+[guid]::NewGuid().ToString('N')+'.bak') -ErrorAction Stop"
  if errorlevel 1 exit /b 2
)
"%SW_CSC%" /nologo /codepage:65001 /target:exe /platform:x64 /optimize+ /out:SolidWorksLocal.exe /reference:System.Web.Extensions.dll /reference:System.Core.dll src\Protocol.cs src\PartPlan.cs src\TurnedPartPlan.cs src\ContourPartPlan.cs src\ProfilePartPlan.cs src\SolidWorksReader.cs src\TestExperiment.cs src\Program.cs src\Tests.cs
if errorlevel 1 (
  echo BUILD FAILED. Close the connector in Codex before rebuilding.
  exit /b 2
)
SolidWorksLocal.exe --self-test
if errorlevel 1 exit /b 2
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0TEST_ASSEMBLY_READ_REGRESSIONS.ps1"
if errorlevel 1 exit /b 2
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0TEST_WRITE_SAFETY_REGRESSIONS.ps1"
if errorlevel 1 exit /b 2
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0TEST_SCOPED_EXPERIMENT.ps1"
exit /b %errorlevel%
