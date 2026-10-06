$ErrorActionPreference = 'Continue'
$repo = "G:\Mine\Desktop\SolidWorksCodex-Git"
Set-Location $repo
$exe = Join-Path $repo 'SolidWorksLocal.exe'
$reportPath = Join-Path $repo '_claude_live_test_dataset_report.txt'
if (Test-Path -LiteralPath $reportPath) { Remove-Item -LiteralPath $reportPath -Force }
function Log($text) { Add-Content -LiteralPath $reportPath -Value $text -Encoding UTF8 }

# One live SOLIDWORKS test per Plan type actually used in the newly authored drawing-plans
# (ContourPartPlan, PartPlan, TurnedPartPlan). ProfilePartPlan already has a PASSing control
# test on record (_claude_profile_control_test_report.txt) -- not repeated here.
#
# Hardening after the 2026-09-13 incident (SolidWorksLocal.exe worker hung indefinitely while
# two things touched SOLIDWORKS at once):
#   - This script NEVER launches SOLIDWORKS itself. It requires exactly one SLDWORKS.exe
#     already running in this Windows session and refuses to proceed otherwise.
#   - Every worker is started and waited on ONE AT A TIME: start -> wait for exit (bounded) ->
#     check exit code -> parse JSON -> only then move to the next case. No parallel or
#     background worker processes.
#   - Each worker call is bounded by an explicit timeout. On timeout, ONLY that worker
#     process is killed (never SOLIDWORKS, never Codex/ChatGPT); the result is logged as
#     TIMEOUT and the script moves on -- no automatic retry.
#   - The connector itself (src/SolidWorksReader.cs) now serializes all COM operations across
#     ALL worker processes (this script, --stdio child workers, concurrent Codex/Claude
#     sessions) with a single named mutex, returning CONNECTOR_BUSY on contention instead of
#     racing GetActiveObject / hanging. See BATCH_VALIDATE-style compile via BUILD.cmd and
#     TEST_CONNECTOR_MUTEX_CONCURRENCY.ps1 for proof.

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
    @{ Tool = 'sw_create_sheet_from_contours';    File = 'drawing-plans\00.ST.05.03.00.05.json'; Label = 'ContourPartPlan (00.ST.05.03.00.05, Вставка, 55x9x3mm rect, no holes)' },
    @{ Tool = 'sw_create_part_from_plan';          File = 'drawing-plans\878.ST.02.02.05.04.json'; Label = 'PartPlan (878.ST.02.02.05.04, Гайка, chamfered square block, 1 hole)' },
    @{ Tool = 'sw_create_turned_part_from_plan';   File = 'drawing-plans\878.ST.04.04.00.09.json'; Label = 'TurnedPartPlan (878.ST.04.04.00.09, Вал, stepped shaft, 880mm)' }
)
$perCallTimeoutMs = 60000

foreach ($case in $cases) {
    $requestId = [guid]::NewGuid().ToString('N')
    Log ('===== ' + $case.Label + ' =====')
    Log ('request_id=' + $requestId + ' tool=' + $case.Tool + ' file=' + $case.File)
    $startUtc = [DateTime]::UtcNow
    try {
        $doc = Get-Content -LiteralPath $case.File -Raw -Encoding UTF8 | ConvertFrom-Json
        $planObj = $doc.plan
        $json = $planObj | ConvertTo-Json -Depth 20 -Compress
        $payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))

        $stdOutFile = Join-Path $repo ('_claude_live_test_' + $requestId + '.out.txt')
        $stdErrFile = Join-Path $repo ('_claude_live_test_' + $requestId + '.err.txt')
        $psi = @{
            FilePath               = $exe
            ArgumentList           = @('--worker', $case.Tool, $payload)
            WorkingDirectory       = $repo
            PassThru               = $true
            NoNewWindow            = $true
            RedirectStandardOutput = $stdOutFile
            RedirectStandardError  = $stdErrFile
        }
        $proc = Start-Process @psi
        Log ('worker_pid=' + $proc.Id)
        $finished = $proc.WaitForExit($perCallTimeoutMs)
        $endUtc = [DateTime]::UtcNow
        if (-not $finished) {
            # Kill ONLY this worker process we just started. Never SOLIDWORKS, never Codex.
            try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch { }
            Log ('RESULT: TIMEOUT after ' + $perCallTimeoutMs + ' ms - worker process (pid=' + $proc.Id + ') killed. SOLIDWORKS was NOT touched by this script. No automatic retry.')
            Log ''
            continue
        }
        $exitCode = $proc.ExitCode
        $raw = ''
        if (Test-Path -LiteralPath $stdOutFile) { $raw = (Get-Content -LiteralPath $stdOutFile -Raw -Encoding UTF8) }
        $errText = ''
        if (Test-Path -LiteralPath $stdErrFile) { $errText = (Get-Content -LiteralPath $stdErrFile -Raw -Encoding UTF8) }
        Remove-Item -LiteralPath $stdOutFile -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $stdErrFile -Force -ErrorAction SilentlyContinue

        Log ('exit_code=' + $exitCode + ' duration_ms=' + [long](($endUtc - $startUtc).TotalMilliseconds))
        Log 'RAW RESPONSE:'
        Log $raw
        if ($errText) { Log ('STDERR: ' + $errText) }
        Log ''

        $result = $null
        try { $result = $raw | ConvertFrom-Json } catch { Log ("JSON PARSE FAILED: " + $_) }

        if ($null -eq $result -or -not $result.ok) {
            $code = $null
            if ($result -and $result.error) { $code = [string]$result.error.code }
            Log ('RESULT: FAIL - tool call did not return ok=true.' + $(if ($code) { ' code=' + $code } else { '' }))
        }
        else {
            $data = $result.data
            $path = [string]$data.file_path
            $expectedVol = [double]$doc.expected_volume_m3
            $actualVol = $null
            if ($data.verification -and $data.verification.actual_volume_m3) { $actualVol = [double]$data.verification.actual_volume_m3 }
            elseif ($data.verification -and $data.verification.axisymmetric_actual_volume_m3) { $actualVol = [double]$data.verification.axisymmetric_actual_volume_m3 }
            elseif ($data.verification -and $data.verification.final_volume_m3) { $actualVol = [double]$data.verification.final_volume_m3 }
            elseif ($data.plan -and $data.plan.calculated -and $data.plan.calculated.net_volume_m3) { $actualVol = [double]$data.plan.calculated.net_volume_m3 }
            elseif ($data.plan -and $data.plan.calculated -and $data.plan.calculated.axisymmetric_volume_m3) { $actualVol = [double]$data.plan.calculated.axisymmetric_volume_m3 }
            $volOk = $false
            if ($actualVol -ne $null -and $expectedVol -gt 0) {
                $volOk = ([Math]::Abs($actualVol - $expectedVol) / $expectedVol -lt 0.01)
            }
            Log ("file_path: " + $path)
            Log ("output file exists: " + (Test-Path -LiteralPath $path))
            Log ("expected_volume_m3 (from plan doc): " + $expectedVol)
            Log ("actual_volume_m3 (from tool response): " + $actualVol)
            Log ("volume within 1%: " + $volOk)
            if ((Test-Path -LiteralPath $path) -and $volOk) {
                Log 'RESULT: PASS'
            } else {
                Log 'RESULT: FAIL - see details above'
            }
        }
    }
    catch {
        Log ("UNHANDLED EXCEPTION: " + $_.ToString())
        Log 'RESULT: FAIL - unhandled exception'
    }
    Log ''
}
Add-Content -LiteralPath $reportPath -Value 'ALL DONE' -Encoding UTF8
