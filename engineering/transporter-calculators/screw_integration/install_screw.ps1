$ErrorActionPreference = 'Stop'
$sourceDir = $PSScriptRoot
$targetDir = 'D:\CodexProjects\transporter_calculator_v4\transporter_calculator_v4_online_cost_package'
if (-not (Test-Path -LiteralPath (Join-Path $targetDir 'run_local.py'))) { throw 'Target calculator not found' }
$backupDir = Join-Path $targetDir ('backups\before_screw_v6_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$files = @('transporter_app_local.py','screw_engine.py','screw_ui.py','test_screw.py','SCREW_V6.md')
foreach ($name in $files) {
    $existingFile = Join-Path $targetDir $name
    if (Test-Path -LiteralPath $existingFile) { Copy-Item -LiteralPath $existingFile -Destination $backupDir }
}
$referenceDir = Join-Path $targetDir 'references\screw_conveyors'
New-Item -ItemType Directory -Path $referenceDir -Force | Out-Null
$snapshotTarget = Join-Path $referenceDir 'workbook_v11.json'
if (Test-Path -LiteralPath $snapshotTarget) { Copy-Item -LiteralPath $snapshotTarget -Destination $backupDir }
foreach ($name in $files) { Copy-Item -LiteralPath (Join-Path $sourceDir $name) -Destination (Join-Path $targetDir $name) -Force }
Copy-Item -LiteralPath (Join-Path $sourceDir 'references\screw_conveyors\workbook_v11.json') -Destination $snapshotTarget -Force
$env:PYTHONPATH = Join-Path $targetDir '.deps'
$env:STREAMLIT_GLOBAL_DEVELOPMENT_MODE = 'false'
$env:STREAMLIT_LOGGER_LEVEL = 'error'
Push-Location -LiteralPath $targetDir
try {
    & 'C:\Users\davos\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 -m unittest test_screw test_local_app test_cost_engine_v4 -v *> (Join-Path $targetDir 'regression-results-v6.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Regression tests failed; see regression-results-v6.txt. Server not restarted.' }
    & (Join-Path $targetDir 'stop_local.ps1')
    & 'C:\Users\davos\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 (Join-Path $targetDir 'run_local.py') --no-browser
    if ($LASTEXITCODE -ne 0) { throw 'Server start failed' }
    Get-Content -LiteralPath (Join-Path $targetDir 'regression-results-v6.txt') -Tail 8
    Write-Output ('Backup: ' + $backupDir)
} finally { Pop-Location }
