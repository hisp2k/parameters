$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$reportPath = Join-Path $root '_claude_diag_processes_report.txt'
if (Test-Path -LiteralPath $reportPath) { Remove-Item -LiteralPath $reportPath -Force }
function Log($text) { Add-Content -LiteralPath $reportPath -Value $text -Encoding UTF8 }

Log ("TIMESTAMP: " + (Get-Date -Format 'o'))
Log ''
Log 'PROCESSES (SLDWORKS, SolidWorksLocal, powershell, cmd, WerFault):'
Get-Process | Where-Object { $_.ProcessName -match 'SLDWORKS|SolidWorksLocal|powershell|cmd|WerFault|conhost' } |
    ForEach-Object { Log ("  " + $_.ProcessName + " pid=" + $_.Id + " mainWindowTitle='" + $_.MainWindowTitle + "' responding=" + $_.Responding + " startTime=" + $_.StartTime) }
Log ''
Add-Content -LiteralPath $reportPath -Value 'DONE' -Encoding UTF8
