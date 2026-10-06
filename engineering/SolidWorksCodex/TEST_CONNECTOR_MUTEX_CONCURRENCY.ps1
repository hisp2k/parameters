$ErrorActionPreference = 'Continue'
$repo = "G:\Mine\Desktop\SolidWorksCodex-Git"
Set-Location $repo
$exe = Join-Path $repo 'SolidWorksLocal.exe'
$reportPath = Join-Path $repo '_claude_mutex_concurrency_report.txt'
if (Test-Path -LiteralPath $reportPath) { Remove-Item -LiteralPath $reportPath -Force }
function Log($text) { Add-Content -LiteralPath $reportPath -Value $text -Encoding UTF8 }

# Proof for the 2026-09-13 concurrency fix: fire THREE sw_create_* worker requests at the
# same time (this is the one script that intentionally starts workers concurrently -- it
# exists specifically to prove src/SolidWorksReader.cs's new named COM mutex works) and show
# either (a) their actual COM execution windows, as recorded in the connector's own
# Reports\connector_calls.log, never overlap, or (b) at least one of them is rejected with
# CONNECTOR_BUSY instead of racing SOLIDWORKS or hanging. This script itself never launches
# SOLIDWORKS and never kills SOLIDWORKS/Codex -- only worker processes it started, and only on
# its own bounded timeout.

function Get-SolidWorksProcesses { @(Get-Process -Name 'SLDWORKS' -ErrorAction SilentlyContinue) }

$swProcs = Get-SolidWorksProcesses
if ($swProcs.Count -eq 0) {
    Log 'SOLIDWORKS_NOT_RUNNING: запустите SOLIDWORKS через меню Пуск и повторите тест.'
    Add-Content -LiteralPath $reportPath -Value 'ALL DONE (aborted before any worker call)' -Encoding UTF8
    exit 3
}
if ($swProcs.Count -gt 1) {
    Log ('MULTIPLE_SOLIDWORKS: найдено ' + $swProcs.Count + ' процессов SLDWORKS.exe. Оставьте один экземпляр и повторите тест.')
    Add-Content -LiteralPath $reportPath -Value 'ALL DONE (aborted before any worker call)' -Encoding UTF8
    exit 3
}
Log ('Pre-check OK: exactly one SLDWORKS.exe running, pid=' + $swProcs[0].Id)
Log ''

$cases = @(
    @{ Tool = 'sw_create_sheet_from_contours';    File = 'drawing-plans\00.ST.05.03.00.05.json' },
    @{ Tool = 'sw_create_part_from_plan';          File = 'drawing-plans\878.ST.02.02.05.04.json' },
    @{ Tool = 'sw_create_turned_part_from_plan';   File = 'drawing-plans\878.ST.04.04.00.09.json' }
)
$perCallTimeoutMs = 90000
$launched = @()

Log '===== launching 3 workers concurrently (Start-Process, no wait between launches) ====='
foreach ($case in $cases) {
    $doc = Get-Content -LiteralPath $case.File -Raw -Encoding UTF8 | ConvertFrom-Json
    $json = $doc.plan | ConvertTo-Json -Depth 20 -Compress
    $payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
    $tag = [guid]::NewGuid().ToString('N')
    $stdOutFile = Join-Path $repo ('_claude_mutex_test_' + $tag + '.out.txt')
    $stdErrFile = Join-Path $repo ('_claude_mutex_test_' + $tag + '.err.txt')
    $psi = @{
        FilePath               = $exe
        ArgumentList           = @('--worker', $case.Tool, $payload)
        WorkingDirectory       = $repo
        PassThru               = $true
        NoNewWindow            = $true
        RedirectStandardOutput = $stdOutFile
        RedirectStandardError  = $stdErrFile
    }
    $launchUtc = [DateTime]::UtcNow
    $proc = Start-Process @psi
    Log ('launched tool=' + $case.Tool + ' worker_pid=' + $proc.Id + ' launch_utc=' + $launchUtc.ToString('o'))
    $launched += [ordered]@{ Tool = $case.Tool; Proc = $proc; StdOut = $stdOutFile; StdErr = $stdErrFile; LaunchUtc = $launchUtc }
}
Log ''
Log '===== waiting for all 3 (bounded, one at a time; not a race on our side) ====='

$results = @()
foreach ($item in $launched) {
    $finished = $item.Proc.WaitForExit($perCallTimeoutMs)
    $endUtc = [DateTime]::UtcNow
    if (-not $finished) {
        try { Stop-Process -Id $item.Proc.Id -Force -ErrorAction SilentlyContinue } catch { }
        Log ('worker_pid=' + $item.Proc.Id + ' tool=' + $item.Tool + ' RESULT=TIMEOUT (killed only this worker; SOLIDWORKS untouched)')
        $results += [ordered]@{ Tool = $item.Tool; Pid = $item.Proc.Id; Result = 'TIMEOUT' }
        continue
    }
    $exitCode = $item.Proc.ExitCode
    $raw = ''
    if (Test-Path -LiteralPath $item.StdOut) { $raw = Get-Content -LiteralPath $item.StdOut -Raw -Encoding UTF8 }
    $errText = ''
    if (Test-Path -LiteralPath $item.StdErr) { $errText = Get-Content -LiteralPath $item.StdErr -Raw -Encoding UTF8 }
    Remove-Item -LiteralPath $item.StdOut -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $item.StdErr -Force -ErrorAction SilentlyContinue
    $parsed = $null
    try { $parsed = $raw | ConvertFrom-Json } catch { }
    $ok = ($parsed -and $parsed.ok -eq $true)
    $code = $null
    if ($parsed -and -not $ok -and $parsed.error) { $code = [string]$parsed.error.code }
    Log ('worker_pid=' + $item.Proc.Id + ' tool=' + $item.Tool + ' exit_code=' + $exitCode + ' ok=' + $ok + $(if ($code) { ' error_code=' + $code } else { '' }))
    if ($errText) { Log ('  stderr: ' + $errText) }
    $results += [ordered]@{ Tool = $item.Tool; Pid = $item.Proc.Id; Result = $(if ($ok) { 'OK' } elseif ($code) { $code } else { 'FAIL' }) }
}
Log ''
Log '===== relevant lines from Reports\connector_calls.log (joined by worker_pid) ====='
$logPath = Join-Path $repo 'Reports\connector_calls.log'
if (Test-Path -LiteralPath $logPath) {
    $lines = Get-Content -LiteralPath $logPath -Encoding UTF8
    foreach ($item in $launched) {
        $needle = 'worker_pid=' + $item.Proc.Id + ' '
        $match = $lines | Where-Object { $_ -like ('*' + $needle + '*') } | Select-Object -Last 1
        if ($match) { Log $match } else { Log ('(no connector_calls.log entry found for worker_pid=' + $item.Proc.Id + ')') }
    }
} else {
    Log '(Reports\connector_calls.log does not exist)'
}
Log ''
$busyCount = @($results | Where-Object { $_.Result -eq 'CONNECTOR_BUSY' }).Count
$okCount = @($results | Where-Object { $_.Result -eq 'OK' }).Count
Log ("SUMMARY: ok=" + $okCount + " connector_busy=" + $busyCount + " other=" + (@($results).Count - $okCount - $busyCount))
Log 'Serialization proof: compare the start=/end= timestamps in the connector_calls.log lines above for overlap (see analysis notes), or note that CONNECTOR_BUSY appeared above instead of a race/hang.'
Add-Content -LiteralPath $reportPath -Value 'ALL DONE' -Encoding UTF8
