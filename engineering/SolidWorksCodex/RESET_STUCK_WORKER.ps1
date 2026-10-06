$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$reportPath = Join-Path $root '_claude_reset_worker_report.txt'
if (Test-Path -LiteralPath $reportPath) { Remove-Item -LiteralPath $reportPath -Force }
function Log($text) { Add-Content -LiteralPath $reportPath -Value $text -Encoding UTF8 }

# The previous OPEN_WORKSPACE_DOC_CAPTURE run's SolidWorksLocal.exe worker
# process never returned (confirmed via DIAG_PROCESSES: it has been running
# for 10+ minutes while still reporting Responding=True, with no modal
# dialog visible anywhere on either monitor and SOLIDWORKS itself showing no
# open document). It is almost certainly blocked inside a COM call that will
# never complete on its own. This process only ever attempted to OPEN a file
# (read-only intent) -- it never reached any save/edit code path, so
# terminating it cannot corrupt or lose any document content.
Log ("TIMESTAMP: " + (Get-Date -Format 'o'))
$stuck = Get-Process -Name 'SolidWorksLocal' -ErrorAction SilentlyContinue
if ($stuck) {
    foreach ($p in $stuck) {
        Log ("Stopping stuck SolidWorksLocal.exe pid=" + $p.Id + " startTime=" + $p.StartTime)
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    }
} else {
    Log 'No SolidWorksLocal.exe process found.'
}
Start-Sleep -Seconds 2
$after = Get-Process -Name 'SolidWorksLocal' -ErrorAction SilentlyContinue
Log ("SolidWorksLocal processes remaining after stop: " + (@($after).Count))
$sw = Get-Process -Name 'SLDWORKS' -ErrorAction SilentlyContinue
Log ("SLDWORKS processes still running: " + (@($sw).Count))
Add-Content -LiteralPath $reportPath -Value 'DONE' -Encoding UTF8
