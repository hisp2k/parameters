$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$testDir = Join-Path $repo "_bridge_test"
$out = "$repo\_claude_bridge_tests_report.txt"
if (Test-Path $out) { Remove-Item $out -Force }
$results = New-Object System.Collections.Generic.List[object]

function Sec([string]$t) { "" | Out-File $out -Append -Encoding utf8; "===== $t =====" | Out-File $out -Append -Encoding utf8 }
function Log($t) { $t | Out-File $out -Append -Encoding utf8 }
function Record([string]$name, [bool]$pass, [string]$detail) {
    $results.Add([pscustomobject]@{ name = $name; pass = $pass; detail = $detail })
    Log ("[{0}] {1} -- {2}" -f ($(if ($pass) {"PASS"} else {"FAIL"})), $name, $detail)
}

# --- 0. set up isolated test sandbox: fake worker instead of the real exe ---
Sec "setup"
if (Test-Path $testDir) { Remove-Item $testDir -Recurse -Force }
New-Item -ItemType Directory -Path $testDir | Out-Null
New-Item -ItemType Directory -Path (Join-Path $testDir "ClaudeBridge") | Out-Null
New-Item -ItemType Directory -Path (Join-Path $testDir "ClaudeBridge\responses") | Out-Null
Copy-Item -LiteralPath (Join-Path $repo "CLAUDE_CALL.ps1") -Destination (Join-Path $testDir "CLAUDE_CALL.ps1")
Copy-Item -LiteralPath (Join-Path $repo "FakeWorker.cs") -Destination (Join-Path $testDir "FakeWorker.cs")

$csc = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) { Log "FATAL: csc.exe not found, cannot build FakeWorker"; "ALL DONE (setup failed)" | Out-File "$repo\_claude_bridge_tests_DONE.txt" -Encoding utf8; exit 1 }
$buildOut = & $csc /nologo /target:exe /platform:x64 /out:"$testDir\SolidWorksLocal.exe" "$testDir\FakeWorker.cs" 2>&1 | Out-String
Log "FakeWorker build output: $buildOut"
if (-not (Test-Path "$testDir\SolidWorksLocal.exe")) { Log "FATAL: FakeWorker did not build"; "ALL DONE (build failed)" | Out-File "$repo\_claude_bridge_tests_DONE.txt" -Encoding utf8; exit 1 }
Log "FakeWorker built OK."

$callScript = Join-Path $testDir "CLAUDE_CALL.ps1"
$reqPath = Join-Path $testDir "ClaudeBridge\request.json"
$respPath = Join-Path $testDir "ClaudeBridge\response.json"
$responsesDir = Join-Path $testDir "ClaudeBridge\responses"
$lockPath = Join-Path $testDir "ClaudeBridge\worker.lock"
$quarantinePath = Join-Path $testDir "ClaudeBridge\quarantine.json"
$stderrLogPath = Join-Path $testDir "ClaudeBridge\worker_stderr.log"

# Reads the authoritative per-request-id response file
# (ClaudeBridge\responses\<request_id>.json). response.json is deliberately
# never read by this helper: per item 2 of the audit it is only a
# best-effort compatibility copy of the latest result and must never be used
# to match a request to its answer -- if the bridge regressed and started
# sharing one response again, reading only the per-id file is what would
# catch that regression instead of silently passing.
function Invoke-Bridge([hashtable]$requestObj) {
    if (-not $requestObj.ContainsKey('request_id') -or [string]::IsNullOrWhiteSpace([string]$requestObj['request_id'])) {
        $requestObj['request_id'] = [Guid]::NewGuid().ToString('N')
    }
    $rid = [string]$requestObj['request_id']
    $perRequestPath = Join-Path $responsesDir "$rid.json"
    if (Test-Path $perRequestPath) { Remove-Item $perRequestPath -Force }
    $json = $requestObj | ConvertTo-Json -Depth 10 -Compress
    [IO.File]::WriteAllText($reqPath, $json, (New-Object Text.UTF8Encoding($false)))
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $callScript | Out-Null
    $code = $LASTEXITCODE
    $resp = $null
    if (Test-Path $perRequestPath) {
        try { $resp = Get-Content -LiteralPath $perRequestPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { }
    }
    return @{ ExitCode = $code; Response = $resp; RequestId = $rid; ResponsePath = $perRequestPath }
}

function Read-LockOwner {
    if (-not (Test-Path -LiteralPath $lockPath)) { return $null }
    $lockPid = $null; $token = $null
    foreach ($line in (Get-Content -LiteralPath $lockPath -ErrorAction SilentlyContinue)) {
        if ($line -match '^pid=(\d+)$') { $lockPid = [int]$Matches[1] }
        if ($line -match '^token=(.+)$') { $token = $Matches[1].Trim() }
    }
    return [pscustomobject]@{ Pid = $lockPid; Token = $token }
}

# --- 1. success ---
Sec "1. success (fake_ok)"
$r = Invoke-Bridge @{ tool = 'fake_ok'; arguments = @{ n = 1 } }
$pass = ($r.ExitCode -eq 0) -and $r.Response -and ($r.Response.ok -eq $true) -and ($r.Response.status -eq 'OK') -and ($r.Response.result.ok -eq $true) -and ($r.Response.request_id -eq $r.RequestId)
Record "success" $pass "exit=$($r.ExitCode) ok=$($r.Response.ok) status=$($r.Response.status) request_id_matches=$($r.Response.request_id -eq $r.RequestId)"

# --- 2. result.ok=false (well-formed tool failure) ---
Sec "2. result.ok=false (fake_fail)"
$r = Invoke-Bridge @{ tool = 'fake_fail'; arguments = @{} }
$pass = ($r.ExitCode -eq 1) -and $r.Response -and ($r.Response.ok -eq $false) -and ($r.Response.status -eq 'TOOL_FAILED') -and ($r.Response.result.ok -eq $false) -and ($r.Response.result.error.code -eq 'FAKE_FAIL')
Record "result.ok=false" $pass "exit=$($r.ExitCode) ok=$($r.Response.ok) status=$($r.Response.status) errcode=$($r.Response.result.error.code)"

# --- 3. worker exit code != 0 (even though its JSON falsely claims ok:true) ---
Sec "3. worker exit code != 0 (fake_nonzero)"
$r = Invoke-Bridge @{ tool = 'fake_nonzero'; arguments = @{} }
$pass = ($r.ExitCode -eq 1) -and $r.Response -and ($r.Response.ok -eq $false) -and ($r.Response.worker_exit_code -eq 3) -and ($r.Response.status -eq 'TOOL_FAILED')
Record "worker exit code != 0 overrides a false ok:true" $pass "exit=$($r.ExitCode) bridge_ok=$($r.Response.ok) worker_exit_code=$($r.Response.worker_exit_code)"

# --- 4. corrupted JSON from worker ---
Sec "4. corrupted JSON (fake_corrupt)"
$r = Invoke-Bridge @{ tool = 'fake_corrupt'; arguments = @{} }
$pass = ($r.ExitCode -eq 2) -and $r.Response -and ($r.Response.ok -eq $false) -and ($r.Response.status -eq 'BRIDGE_ERROR') -and (-not [string]::IsNullOrWhiteSpace([string]$r.Response.parse_error)) -and (-not [string]::IsNullOrWhiteSpace([string]$r.Response.raw_output))
Record "corrupted JSON" $pass "exit=$($r.ExitCode) status=$($r.Response.status) parse_error_set=$(-not [string]::IsNullOrWhiteSpace([string]$r.Response.parse_error))"

# --- 5. empty response from worker ---
$null = Invoke-Bridge @{ tool = 'bridge_clear_quarantine'; arguments = @{} }
Sec "5. empty stdout (fake_empty)"
$r = Invoke-Bridge @{ tool = 'fake_empty'; arguments = @{} }
$pass = ($r.ExitCode -eq 2) -and $r.Response -and ($r.Response.ok -eq $false) -and ($r.Response.status -eq 'BRIDGE_ERROR') -and ($r.Response.parse_error -eq 'Worker produced no stdout.')
Record "empty response" $pass "exit=$($r.ExitCode) status=$($r.Response.status) parse_error=$($r.Response.parse_error)"

# --- 6. stdout/stderr separation ---
$null = Invoke-Bridge @{ tool = 'bridge_clear_quarantine'; arguments = @{} }
Sec "6. stdout/stderr separation (fake_stderr_noise)"
if (Test-Path $stderrLogPath) { Remove-Item $stderrLogPath -Force }
$r = Invoke-Bridge @{ tool = 'fake_stderr_noise'; arguments = @{} }
$stderrCaptured = (Test-Path $stderrLogPath) -and ((Get-Content -LiteralPath $stderrLogPath -Raw) -match 'diagnostic noise line 1')
$pass = ($r.ExitCode -eq 0) -and $r.Response -and ($r.Response.ok -eq $true) -and $stderrCaptured
Record "stdout/stderr separation" $pass "exit=$($r.ExitCode) ok=$($r.Response.ok) stderr_log_has_noise=$stderrCaptured"

# --- 7. timeout -> UNKNOWN, worker killed, no false cancel claim, quarantine set ---
Sec "7. timeout (fake_hang, timeout_ms=2000) -> quarantine"
if (Test-Path $quarantinePath) { Remove-Item $quarantinePath -Force }
$sw = [Diagnostics.Stopwatch]::StartNew()
$r = Invoke-Bridge @{ tool = 'fake_hang'; arguments = @{}; timeout_ms = 2000 }
$sw.Stop()
Start-Sleep -Milliseconds 500
$hangStillRunning = @(Get-Process -Name (Get-Item "$testDir\SolidWorksLocal.exe").BaseName -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq (Resolve-Path "$testDir\SolidWorksLocal.exe").Path }).Count -gt 0
# Note: the message is EXPECTED to mention "cancelled"/"rolled back" in a
# negated form ("this is not a claim that anything was cancelled or rolled
# back") -- that explicit disclaimer is exactly what the audit asked for. So
# this check asserts the STRUCTURAL guarantees (status/code/no hung process/
# bounded wall time/quarantine written) rather than pattern-matching prose,
# and separately confirms the message does not make a bare positive claim of
# success.
$falseSuccessClaim = ($r.Response.error.message -match 'successfully (cancel|roll)') -or ($r.Response.status -eq 'CANCELLED') -or ($r.Response.status -eq 'ROLLED_BACK')
$quarantineWritten = Test-Path -LiteralPath $quarantinePath
$pass = ($r.ExitCode -eq 2) -and $r.Response -and ($r.Response.status -eq 'UNKNOWN') -and ($r.Response.error.code -eq 'TIMEOUT') -and ($sw.Elapsed.TotalMilliseconds -lt 15000) -and (-not $hangStillRunning) -and (-not $falseSuccessClaim) -and $quarantineWritten
Record "timeout -> UNKNOWN, process reaped, no false cancel claim, quarantine written" $pass "exit=$($r.ExitCode) status=$($r.Response.status) elapsed_ms=$([int]$sw.Elapsed.TotalMilliseconds) still_running=$hangStillRunning quarantine_written=$quarantineWritten"


# --- 7b. quarantine blocks a write-capable call, allows a read-only tool,
#         then bridge_clear_quarantine clears it and normal calls resume ---
Sec "7b. quarantine gate (write-capable blocked, read-only allowed, clear resumes)"
$rBlocked = Invoke-Bridge @{ tool = 'fake_ok'; arguments = @{} }
$blockedOk = ($rBlocked.ExitCode -eq 2) -and $rBlocked.Response -and ($rBlocked.Response.status -eq 'QUARANTINED') -and ($rBlocked.Response.error.code -eq 'QUARANTINED_AFTER_TIMEOUT')
$rReadOnly = Invoke-Bridge @{ tool = 'sw_status'; arguments = @{} }
# FakeWorker has no sw_status case, so it falls to its "default" branch and
# returns ok:false/UNKNOWN_FAKE_TOOL with worker exit 0 -- what matters here
# is only that the QUARANTINE GATE itself let the call through to the worker
# (status is not QUARANTINED/QUARANTINED_AFTER_TIMEOUT) rather than refusing
# it outright, proving the read-only allowlist bypass works.
$readOnlyPassedGate = $rReadOnly.Response -and ($rReadOnly.Response.status -ne 'QUARANTINED') -and ($rReadOnly.Response.error.code -ne 'QUARANTINED_AFTER_TIMEOUT')
$rClear = Invoke-Bridge @{ tool = 'bridge_clear_quarantine'; arguments = @{} }
$clearOk = ($rClear.ExitCode -eq 0) -and $rClear.Response -and ($rClear.Response.ok -eq $true) -and ($rClear.Response.result.data.quarantine_cleared -eq $true) -and (-not (Test-Path -LiteralPath $quarantinePath))
$rResumed = Invoke-Bridge @{ tool = 'fake_ok'; arguments = @{ n = 9 } }
$resumedOk = ($rResumed.ExitCode -eq 0) -and $rResumed.Response -and ($rResumed.Response.ok -eq $true) -and ($rResumed.Response.status -eq 'OK')
$pass = $blockedOk -and $readOnlyPassedGate -and $clearOk -and $resumedOk
Record "quarantine blocks write-capable, allows read-only, clear resumes normal calls" $pass "blocked=$blockedOk read_only_passed_gate=$readOnlyPassedGate cleared=$clearOk resumed=$resumedOk"

# --- 8. repeated request_id across two independent, sequential calls ---
Sec "8. repeated request_id (sequential, different arguments each time)"
$r1 = Invoke-Bridge @{ tool = 'fake_ok'; arguments = @{ n = 111 }; request_id = 'dup-test-id' }
Start-Sleep -Milliseconds 50
$r2 = Invoke-Bridge @{ tool = 'fake_ok'; arguments = @{ n = 222 }; request_id = 'dup-test-id' }
$pass = ($r1.ExitCode -eq 0) -and ($r2.ExitCode -eq 0) -and
    ($r1.Response.request_id -eq 'dup-test-id') -and ($r2.Response.request_id -eq 'dup-test-id') -and
    ($r1.Response.result.data.echo -match '"n":111') -and ($r2.Response.result.data.echo -match '"n":222') -and
    ($r1.Response.completed_at_utc -ne $r2.Response.completed_at_utc)
Record "repeated request_id does not cause stale/cached answers" $pass "r1_echo_has_111=$($r1.Response.result.data.echo -match '111') r2_echo_has_222=$($r2.Response.result.data.echo -match '222') timestamps_differ=$($r1.Response.completed_at_utc -ne $r2.Response.completed_at_utc)"

# --- 8b. an unsafe caller-supplied request_id is rejected outright, never
#         sanitized and reused as a file name ---
Sec "8b. unsafe request_id rejected (path-traversal attempt)"
if (Test-Path $reqPath) { Remove-Item $reqPath -Force }
$unsafeId = '..\..\evil'
$json = (@{ tool = 'fake_ok'; arguments = @{}; request_id = $unsafeId } | ConvertTo-Json -Compress)
[IO.File]::WriteAllText($reqPath, $json, (New-Object Text.UTF8Encoding($false)))
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $callScript | Out-Null
$code = $LASTEXITCODE
$noEscapedFileAnywhere = @(Get-ChildItem -LiteralPath $testDir -Recurse -Filter '*evil*' -ErrorAction SilentlyContinue).Count -eq 0
$pass = ($code -eq 2) -and $noEscapedFileAnywhere
Record "unsafe request_id rejected, never used as a path" $pass "exit=$code no_file_written_for_unsafe_id_anywhere_under_testdir=$noEscapedFileAnywhere"

# --- 9. concurrency: 3 overlapping callers, lock ownership survives BUSY
#        callers untouched, each request_id gets its own response, and the
#        bridge is usable again once the winner finishes. This directly
#        tests the item-1 bug (a BUSY caller used to delete the winner's
#        lock) and the item-2 bug (a shared response.json could be
#        overwritten by a losing caller). ---
Sec "9. concurrency: 3 overlapping callers + lock survival + per-id responses"
if (Test-Path $lockPath) { Remove-Item $lockPath -Force }
Get-ChildItem -LiteralPath $responsesDir -Filter 'concurrent-*.json' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

function Start-BridgeCall([string]$requestId, [string]$tool, [int]$delayMs, [int]$timeoutMs) {
    $json = (@{ tool = $tool; arguments = @{}; request_id = $requestId; timeout_ms = $timeoutMs } | ConvertTo-Json -Compress)
    [IO.File]::WriteAllText($reqPath, $json, (New-Object Text.UTF8Encoding($false)))
    $cmd = "`$env:FAKE_DELAY_MS='$delayMs'; & '$callScript'; exit `$LASTEXITCODE"
    return Start-Process -FilePath "powershell.exe" -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $cmd) -PassThru -WindowStyle Hidden
}

# Caller 1 (the eventual winner) holds the lock for 6s -- long enough for
# callers 2 and 3 to each attempt and be refused while it is still running.
$proc1 = Start-BridgeCall 'concurrent-1' 'fake_delay_ok' 6000 30000
Start-Sleep -Milliseconds 1500
$lockAfterCall1Started = Read-LockOwner
$lockHeldByCall1 = ($null -ne $lockAfterCall1Started) -and ($null -ne $lockAfterCall1Started.Token)

# Caller 2: must be refused (BRIDGE_BUSY) while caller 1 still holds the lock.
$proc2 = Start-BridgeCall 'concurrent-2' 'fake_ok' 0 10000
$proc2.WaitForExit(10000) | Out-Null
$lockAfterCall2 = Read-LockOwner
$lockUnchangedAfterCall2 = $lockHeldByCall1 -and ($null -ne $lockAfterCall2) -and
    ($lockAfterCall2.Pid -eq $lockAfterCall1Started.Pid) -and ($lockAfterCall2.Token -eq $lockAfterCall1Started.Token)

# Caller 3: started while caller 1 is STILL running (well inside its 6s
# delay) -- must also be refused, and must not disturb the lock either.
$proc3 = Start-BridgeCall 'concurrent-3' 'fake_ok' 0 10000
$proc3.WaitForExit(10000) | Out-Null
$lockAfterCall3 = Read-LockOwner
$lockUnchangedAfterCall3 = $lockHeldByCall1 -and ($null -ne $lockAfterCall3) -and
    ($lockAfterCall3.Pid -eq $lockAfterCall1Started.Pid) -and ($lockAfterCall3.Token -eq $lockAfterCall1Started.Token)

# Now wait for caller 1 (the winner) to actually finish.
$proc1.WaitForExit(20000) | Out-Null
$lockReleasedAfterCall1 = -not (Test-Path -LiteralPath $lockPath)

$resp1Path = Join-Path $responsesDir 'concurrent-1.json'
$resp2Path = Join-Path $responsesDir 'concurrent-2.json'
$resp3Path = Join-Path $responsesDir 'concurrent-3.json'
$resp1 = if (Test-Path $resp1Path) { Get-Content -LiteralPath $resp1Path -Raw -Encoding UTF8 | ConvertFrom-Json } else { $null }
$resp2 = if (Test-Path $resp2Path) { Get-Content -LiteralPath $resp2Path -Raw -Encoding UTF8 | ConvertFrom-Json } else { $null }
$resp3 = if (Test-Path $resp3Path) { Get-Content -LiteralPath $resp3Path -Raw -Encoding UTF8 | ConvertFrom-Json } else { $null }

# Every caller must have its OWN response file with its OWN request_id --
# none lost, none overwritten by another caller's answer.
$distinctResponses = ($null -ne $resp1) -and ($null -ne $resp2) -and ($null -ne $resp3) -and
    ($resp1.request_id -eq 'concurrent-1') -and ($resp2.request_id -eq 'concurrent-2') -and ($resp3.request_id -eq 'concurrent-3')
$call1Won = ($proc1.ExitCode -eq 0) -and ($resp1.ok -eq $true) -and ($resp1.status -eq 'OK')
$call2Busy = ($proc2.ExitCode -eq 2) -and ($resp2.ok -eq $false) -and ($resp2.status -eq 'BRIDGE_BUSY') -and ($resp2.error.code -eq 'BRIDGE_BUSY')
$call3Busy = ($proc3.ExitCode -eq 2) -and ($resp3.ok -eq $false) -and ($resp3.status -eq 'BRIDGE_BUSY') -and ($resp3.error.code -eq 'BRIDGE_BUSY')

# A 4th, sequential call after the winner released its lock must succeed --
# proves BUSY callers never wedged the bridge shut.
$r4 = Invoke-Bridge @{ tool = 'fake_ok'; arguments = @{ n = 4 }; request_id = 'concurrent-4' }
$call4Succeeds = ($r4.ExitCode -eq 0) -and $r4.Response -and ($r4.Response.ok -eq $true) -and ($r4.Response.status -eq 'OK')

$pass = $lockHeldByCall1 -and $lockUnchangedAfterCall2 -and $lockUnchangedAfterCall3 -and $lockReleasedAfterCall1 -and
    $distinctResponses -and $call1Won -and $call2Busy -and $call3Busy -and $call4Succeeds
Record "3-way concurrency: lock survives BUSY callers, 3 distinct responses, bridge usable again after" $pass (
    "lock_held_by_1=$lockHeldByCall1 lock_unchanged_after_2=$lockUnchangedAfterCall2 lock_unchanged_after_3=$lockUnchangedAfterCall3 " +
    "lock_released_after_1=$lockReleasedAfterCall1 distinct_responses=$distinctResponses call1_won=$call1Won call2_busy=$call2Busy call3_busy=$call3Busy call4_succeeds=$call4Succeeds " +
    "proc1_exit=$($proc1.ExitCode) proc2_exit=$($proc2.ExitCode) proc3_exit=$($proc3.ExitCode)"
)

Sec "SUMMARY"
$passCount = ($results | Where-Object { $_.pass }).Count
$totalCount = $results.Count
Log "$passCount / $totalCount scenarios passed"
foreach ($r in $results) { Log ("  [{0}] {1}" -f ($(if ($r.pass) {"PASS"} else {"FAIL"})), $r.name) }

"ALL DONE" | Out-File "$repo\_claude_bridge_tests_DONE.txt" -Encoding utf8

if ($passCount -ne $totalCount) { exit 1 }
exit 0
