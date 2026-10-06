$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$reportPath = Join-Path $root '_claude_diag_sw_status_report.txt'
if (Test-Path -LiteralPath $reportPath) { Remove-Item -LiteralPath $reportPath -Force }
function Log($text) { Add-Content -LiteralPath $reportPath -Value $text -Encoding UTF8 }

Log ("TIMESTAMP: " + (Get-Date -Format 'o'))
Log ("EXE PATH: " + $exe)
Log ("EXE LAST WRITE TIME: " + (Get-Item -LiteralPath $exe).LastWriteTime)
Log ''
try {
    $payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('{}'))
    $raw = (& $exe --worker sw_status $payload 2>&1 | ForEach-Object { $_.ToString() }) -join "`n"
    Log 'RAW RESPONSE:'
    Log $raw
}
catch {
    Log ("EXCEPTION: " + $_.ToString())
}
Add-Content -LiteralPath $reportPath -Value 'DONE' -Encoding UTF8
