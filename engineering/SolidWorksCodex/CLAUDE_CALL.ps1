param([string]$RequestFile)
$ErrorActionPreference = 'Stop'
try {
    [Console]::OutputEncoding = [Text.Encoding]::UTF8
    [Console]::InputEncoding = [Text.Encoding]::UTF8
} catch { }
$OutputEncoding = [Text.Encoding]::UTF8

# =============================================================================
# ClaudeBridge worker launcher -- claude/main-audit-fixes.
#
# Revision 3 (2026-09-13, second review pass) fixes real bugs found by review
# of revision 2's commit aec36e9:
#   - Release-Lock used to delete ClaudeBridge\worker.lock unconditionally,
#     including in the BRIDGE_BUSY path -- a call that lost the race to
#     acquire the lock would then delete the WINNER's lock on its way out,
#     letting a third call in while the winner was still running. Fixed with
#     explicit lock ownership tracking ($lockOwned, only set true by a
#     successful Try-AcquireLock) plus a content check (pid+token must match
#     what THIS process wrote) before any delete.
#   - All concurrent callers shared one ClaudeBridge\response.json, so two
#     overlapping calls could overwrite each other's answer. Fixed: each
#     call's authoritative answer is now its own
#     ClaudeBridge\responses\<request_id>.json; response.json is kept only as
#     a best-effort compatibility copy of the latest result and must never be
#     used to match a request to its answer.
#   - The response used to be published AFTER the lock was released, leaving
#     a window where a new call could start before the previous answer was
#     even visible. Fixed: publish first, release the lock second.
#   - A TIMEOUT used to leave the bridge fully open for the very next call,
#     even though the SOLIDWORKS-side effect of the timed-out call is
#     unknown. Fixed: a TIMEOUT now writes ClaudeBridge\quarantine.json and
#     every later write-capable call is refused until a human runs the safe,
#     worker-free "bridge_clear_quarantine" pseudo-tool (read-only tools
#     still work during quarantine, so sw_status can be used to check on
#     SOLIDWORKS by hand).
#   - After WaitForExit(timeoutMs) returned true, the script used a
#     Start-Sleep(50) guess to let the async stdout/stderr readers catch up.
#     Fixed: call the documented, deterministic WaitForExit() (no timeout)
#     immediately after, which blocks only until the already-exited process's
#     redirected streams finish draining.
#
# Revision 2 (first audit pass) fixed: always-0 exit code, missing
# request_id, non-atomic response write, no concurrency lock, unbounded
# timeout, merged stdout/stderr.
#
# Exit code contract (the ONLY thing a caller should rely on -- do not infer
# success from the script merely finishing):
#   0 = well-formed worker response AND worker exit code 0 AND result.ok=true
#       (a PROVEN successful tool call)
#   1 = well-formed worker response but the tool itself reported failure
#       (result.ok=false) -- the worker ran and answered, the operation did
#       not succeed
#   2 = bridge/infrastructure problem: bad request.json, launch failure,
#       malformed/missing worker output, BRIDGE_BUSY, QUARANTINED, or a
#       timeout. In the timeout case the response status is UNKNOWN, never a
#       claim that anything was "cancelled" or "rolled back" -- we do not
#       have evidence for that.
# =============================================================================

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$bridgeDir = Join-Path $root 'ClaudeBridge'
$requestPath = Join-Path $bridgeDir 'request.json'
if ($RequestFile) { $requestPath = [IO.Path]::GetFullPath($RequestFile) }
$responsePath = Join-Path $bridgeDir 'response.json'
$responsesDir = Join-Path $bridgeDir 'responses'
$lockPath = Join-Path $bridgeDir 'worker.lock'
$diagPath = Join-Path $bridgeDir 'worker_stderr.log'
$quarantinePath = Join-Path $bridgeDir 'quarantine.json'

$BridgeVersion = '3.1'
$DefaultTimeoutMs = 120000
$MinTimeoutMs = 5000
$MaxTimeoutMs = 600000
$RequestIdPattern = '^[A-Za-z0-9_-]{1,64}$'

# Tools whose own schema marks them readOnlyHint=true (verified against a
# live tools/list capture during this audit) -- safe to allow during
# quarantine because they cannot change SOLIDWORKS state, and sw_status /
# sw_document are exactly what a human needs to check on SOLIDWORKS by hand.
$ReadOnlyTools = @(
    'sw_status', 'sw_workspace_status', 'sw_document', 'sw_properties',
    'sw_part', 'sw_parameters', 'sw_features', 'sw_components', 'sw_drawing',
    'sw_open_workspace_file', 'sw_open_local_file'
)

$ExitSuccess = 0
$ExitToolFailed = 1
$ExitBridgeError = 2

[void][IO.Directory]::CreateDirectory($bridgeDir)
[void][IO.Directory]::CreateDirectory($responsesDir)

$script:lockOwned = $false
$script:lockToken = $null

function New-RequestId { return [Guid]::NewGuid().ToString('N') }

# Atomic publish: write to a uniquely-named temp file IN THE SAME DIRECTORY
# as the destination (so Move-Item is a same-volume rename, which is atomic),
# then rename over the destination.
function Write-JsonAtomic([string]$targetPath, $object) {
    $json = $object | ConvertTo-Json -Depth 64 -Compress
    $dir = Split-Path -Parent $targetPath
    $name = Split-Path -Leaf $targetPath
    $tmp = Join-Path $dir (".$name.tmp.$PID.$([Guid]::NewGuid().ToString('N'))")
    [IO.File]::WriteAllText($tmp, $json + "`r`n", (New-Object Text.UTF8Encoding($false)))
    Move-Item -LiteralPath $tmp -Destination $targetPath -Force
}

# The per-request-id file is the ONLY authoritative answer. response.json is
# a convenience copy of the latest result for a human glancing at the
# folder; a caller matching a request to its answer MUST use
# responses\<request_id>.json, never response.json.
function Write-BridgeResponse($object, [string]$safeRequestId) {
    $perRequestPath = Join-Path $responsesDir "$safeRequestId.json"
    Write-JsonAtomic $perRequestPath $object
    try { Write-JsonAtomic $responsePath $object } catch { }
}

# Deletes worker.lock ONLY if this process actually created it: $lockOwned
# must be true (set only by a successful Try-AcquireLock in THIS process),
# and the lock file's own content must still show this process's pid and the
# exact token this process wrote. A call that received BRIDGE_BUSY never set
# $lockOwned, so it can never reach the delete -- it cannot touch a lock it
# does not own, no matter what order things happen in.
function Release-Lock {
    if (-not $script:lockOwned) { return }
    try {
        if (Test-Path -LiteralPath $lockPath) {
            $ownerPid = $null; $ownerToken = $null
            foreach ($line in (Get-Content -LiteralPath $lockPath -ErrorAction SilentlyContinue)) {
                if ($line -match '^pid=(\d+)$') { $ownerPid = [int]$Matches[1] }
                if ($line -match '^token=(.+)$') { $ownerToken = $Matches[1].Trim() }
            }
            if ($null -ne $script:lockToken -and $ownerPid -eq $PID -and $ownerToken -eq $script:lockToken) {
                Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
            }
            # Content did not match what we wrote (e.g. someone else reclaimed
            # a stale lock in a race, or the file was replaced) -- leave it
            # alone. Deleting a lock we do not currently, verifiably own is
            # exactly the bug this revision fixes.
        }
    } catch { }
    $script:lockOwned = $false
}

# Publish the response BEFORE releasing the lock, so there is no window in
# which the lock is free but the answer is not yet visible on disk -- a
# racing caller could otherwise acquire the lock and start its own worker
# before this call's result exists at all.
function Exit-WithResponse($object, [int]$code, [string]$safeRequestId) {
    Write-BridgeResponse $object $safeRequestId
    Release-Lock
    exit $code
}

function Try-AcquireLock {
    for ($attempt = 0; $attempt -lt 2; $attempt++) {
        $token = [Guid]::NewGuid().ToString('N')
        try {
            $fs = [IO.File]::Open($lockPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
            try {
                $writer = New-Object IO.StreamWriter($fs)
                $writer.WriteLine("pid=$PID")
                $writer.WriteLine("token=$token")
                $writer.WriteLine("acquired_utc=" + [DateTime]::UtcNow.ToString('o'))
                $writer.Flush()
            } finally { $fs.Dispose() }
            $script:lockOwned = $true
            $script:lockToken = $token
            return $true
        } catch [IO.IOException] {
            # Never reclaim a lock by age/PID: its worker may still be changing CAD.
            # An abandoned lock requires inspection, not automatic replay.
            return $false
        } catch {
            return $false
        }
    }
    return $false
}

# -----------------------------------------------------------------------
# 1. Read + validate request.json (no lock needed yet -- nothing external
#    has been touched). Until we have resolved a SAFE request id we cannot
#    write a per-request response file, so these very early failures use a
#    bridge-generated id for the filename only.
# -----------------------------------------------------------------------
$earlyId = New-RequestId
if (-not (Test-Path -LiteralPath $requestPath)) {
    Exit-WithResponse ([ordered]@{
        ok = $false
        status = 'BRIDGE_ERROR'
        request_id = $null
        error = [ordered]@{
            code = 'NO_REQUEST_FILE'
            message = 'No ClaudeBridge\request.json was found. Write a file there shaped like ' +
                '{"tool":"sw_status","arguments":{}} and run this script again.'
        }
        bridge_version = $BridgeVersion
    }) $ExitBridgeError $earlyId
}

$requestedAtUtc = [DateTime]::UtcNow.ToString('o')
$requestRaw = $null
try {
    $requestRaw = Get-Content -LiteralPath $requestPath -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($requestRaw)) { throw 'request.json is empty.' }
} catch {
    Exit-WithResponse ([ordered]@{
        ok = $false
        status = 'BRIDGE_ERROR'
        request_id = $null
        error = [ordered]@{ code = 'EMPTY_OR_UNREADABLE_REQUEST'; message = "Could not read ClaudeBridge\request.json: $($_.Exception.Message)" }
        requested_at_utc = $requestedAtUtc
        bridge_version = $BridgeVersion
    }) $ExitBridgeError $earlyId
}

$request = $null
try {
    $request = $requestRaw | ConvertFrom-Json -ErrorAction Stop
} catch {
    Exit-WithResponse ([ordered]@{
        ok = $false
        status = 'BRIDGE_ERROR'
        request_id = $null
        error = [ordered]@{ code = 'INVALID_REQUEST_JSON'; message = "ClaudeBridge\request.json is not valid JSON: $($_.Exception.Message)" }
        requested_at_utc = $requestedAtUtc
        bridge_version = $BridgeVersion
    }) $ExitBridgeError $earlyId
}

# -----------------------------------------------------------------------
# request_id resolution. A caller-supplied id becomes part of a file path
# (ClaudeBridge\responses\<id>.json), so it MUST be restricted to a safe,
# non-path-traversing character set before it is trusted for that purpose.
# An id that fails this check is a hard error, not a value to sanitize and
# use anyway -- we do not know what the caller intended.
# -----------------------------------------------------------------------
$requestId = $null
$requestIdSource = 'bridge_generated'
$callerSuppliedRaw = $null
if ($request.PSObject.Properties.Name -contains 'request_id' -and -not [string]::IsNullOrWhiteSpace([string]$request.request_id)) {
    $callerSuppliedRaw = [string]$request.request_id
    if ($callerSuppliedRaw -match $RequestIdPattern) {
        $requestId = $callerSuppliedRaw
        $requestIdSource = 'caller'
    } else {
        Exit-WithResponse ([ordered]@{
            ok = $false
            status = 'BRIDGE_ERROR'
            request_id = $null
            error = [ordered]@{
                code = 'INVALID_REQUEST_ID'
                message = 'request_id must match ' + $RequestIdPattern + ' (safe for use as a file name). ' +
                    'The supplied value was rejected rather than sanitized, since a request_id becomes part ' +
                    'of a ClaudeBridge\responses\<request_id>.json path.'
            }
            requested_at_utc = $requestedAtUtc
            bridge_version = $BridgeVersion
        }) $ExitBridgeError $earlyId
    }
} else {
    $requestId = New-RequestId
}
$safeRequestId = $requestId

$tool = $request.tool
if ([string]::IsNullOrWhiteSpace($tool)) {
    Exit-WithResponse ([ordered]@{
        ok = $false
        status = 'BRIDGE_ERROR'
        request_id = $requestId
        request_id_source = $requestIdSource
        error = [ordered]@{ code = 'MISSING_TOOL'; message = 'request.json must have a non-empty "tool" field naming the connector tool to call.' }
        requested_at_utc = $requestedAtUtc
        bridge_version = $BridgeVersion
    }) $ExitBridgeError $safeRequestId
}

# -----------------------------------------------------------------------
# Reserved, worker-free administrative pseudo-tool: clears quarantine after
# a human (or a separate safe check) has confirmed SOLIDWORKS state. This
# never touches SolidWorksLocal.exe, takes the same lock as other requests, and works even
# while quarantined -- it is the only way out of quarantine besides deleting
# the marker file by hand.
# -----------------------------------------------------------------------
if (-not (Try-AcquireLock)) {
    Exit-WithResponse ([ordered]@{
        ok = $false
        status = 'BRIDGE_BUSY'
        request_id = $requestId
        request_id_source = $requestIdSource
        tool = $tool
        arguments = $arguments
        error = [ordered]@{ code = 'BRIDGE_BUSY'; message = 'Another ClaudeBridge call is already in progress (ClaudeBridge\worker.lock exists and its owner may still have a live worker). Inspect abandoned locks before recovery.' }
        requested_at_utc = $requestedAtUtc
        bridge_version = $BridgeVersion
    }) $ExitBridgeError $safeRequestId
}


if ($tool -eq 'bridge_clear_quarantine') {
    $wasQuarantined = Test-Path -LiteralPath $quarantinePath
    if ($wasQuarantined) { try { Remove-Item -LiteralPath $quarantinePath -Force -ErrorAction SilentlyContinue } catch { } }
    Exit-WithResponse ([ordered]@{
        ok = $true
        status = 'OK'
        request_id = $requestId
        request_id_source = $requestIdSource
        tool = $tool
        result = [ordered]@{ ok = $true; data = [ordered]@{ was_quarantined = $wasQuarantined; quarantine_cleared = $true } }
        requested_at_utc = $requestedAtUtc
        completed_at_utc = [DateTime]::UtcNow.ToString('o')
        bridge_version = $BridgeVersion
    }) $ExitSuccess $safeRequestId
}

# -----------------------------------------------------------------------
# Quarantine gate: a prior TIMEOUT left SOLIDWORKS in an unknown state.
# Write-capable tools are refused outright (never even attempted) until
# bridge_clear_quarantine runs. Read-only tools (by schema readOnlyHint)
# still work, since sw_status/sw_document are exactly how a human confirms
# SOLIDWORKS state before clearing quarantine.
# -----------------------------------------------------------------------
$quarantineActive = $false
if (Test-Path -LiteralPath $quarantinePath) {
    $quarantineActive = $true
    if ($ReadOnlyTools -notcontains $tool) {
        $qInfo = $null
        try { $qInfo = Get-Content -LiteralPath $quarantinePath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { }
        Exit-WithResponse ([ordered]@{
            ok = $false
            status = 'QUARANTINED'
            request_id = $requestId
            request_id_source = $requestIdSource
            tool = $tool
            error = [ordered]@{
                code = 'QUARANTINED_AFTER_TIMEOUT'
                message = 'A previous call timed out, so the true state of SOLIDWORKS after that call is not known. ' +
                    'Write-capable tool calls are refused until a human confirms SOLIDWORKS state (read-only tools ' +
                    'such as sw_status still work) and then calls this bridge once with tool=bridge_clear_quarantine.'
            }
            quarantine = $qInfo
            requested_at_utc = $requestedAtUtc
            completed_at_utc = [DateTime]::UtcNow.ToString('o')
            bridge_version = $BridgeVersion
        }) $ExitBridgeError $safeRequestId
    }
}

$arguments = $request.arguments
if ($null -eq $arguments) { $arguments = @{} }

$timeoutMs = $DefaultTimeoutMs
if ($request.PSObject.Properties.Name -contains 'timeout_ms') {
    $requestedTimeout = 0
    if ([int]::TryParse([string]$request.timeout_ms, [ref]$requestedTimeout) -and $requestedTimeout -gt 0) {
        $timeoutMs = [Math]::Min([Math]::Max($requestedTimeout, $MinTimeoutMs), $MaxTimeoutMs)
    }
}

try {
    $argsJson = $arguments | ConvertTo-Json -Depth 64 -Compress
} catch {
    Exit-WithResponse ([ordered]@{
        ok = $false
        status = 'BRIDGE_ERROR'
        request_id = $requestId
        request_id_source = $requestIdSource
        tool = $tool
        error = [ordered]@{ code = 'INVALID_ARGUMENTS_JSON'; message = "arguments could not be re-encoded as JSON: $($_.Exception.Message)" }
        requested_at_utc = $requestedAtUtc
        bridge_version = $BridgeVersion
    }) $ExitBridgeError $safeRequestId
}
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($argsJson))

if (-not (Test-Path -LiteralPath $exe)) {
    Exit-WithResponse ([ordered]@{
        ok = $false
        status = 'BRIDGE_ERROR'
        request_id = $requestId
        request_id_source = $requestIdSource
        tool = $tool
        arguments = $arguments
        error = [ordered]@{ code = 'WORKER_MISSING'; message = 'SolidWorksLocal.exe was not found next to this script. Run BUILD.cmd (or INSTALL.cmd) first.' }
        requested_at_utc = $requestedAtUtc
        completed_at_utc = [DateTime]::UtcNow.ToString('o')
        bridge_version = $BridgeVersion
    }) $ExitBridgeError $safeRequestId
}

# -----------------------------------------------------------------------
# 2. Concurrency lock -- refuse a second simultaneous call outright rather
#    than letting two workers touch the same SOLIDWORKS session at once.
#    A call refused here never sets $lockOwned, so Release-Lock (called via
#    Exit-WithResponse below) is guaranteed to be a no-op for it -- it
#    cannot delete the lock it just failed to acquire.
# -----------------------------------------------------------------------
# -----------------------------------------------------------------------
# 3. Launch the worker with separated, asynchronously-drained stdout/stderr
#    and a bounded wait. Async draining (Begin*ReadLine before WaitForExit)
#    avoids the classic deadlock where the child blocks on a full pipe while
#    nobody is reading it.
# -----------------------------------------------------------------------
$psi = New-Object Diagnostics.ProcessStartInfo
$psi.FileName = $exe
$psi.Arguments = "--worker $tool $payload"
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.StandardOutputEncoding = [Text.Encoding]::UTF8
$psi.StandardErrorEncoding = [Text.Encoding]::UTF8

$proc = New-Object Diagnostics.Process
$proc.StartInfo = $psi
try {
    $proc.Start() | Out-Null
    $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
    $stderrTask = $proc.StandardError.ReadToEndAsync()
} catch {
    Exit-WithResponse ([ordered]@{
        ok = $false
        status = 'BRIDGE_ERROR'
        request_id = $requestId
        request_id_source = $requestIdSource
        tool = $tool
        arguments = $arguments
        error = [ordered]@{ code = 'WORKER_LAUNCH_FAILED'; message = "Could not launch SolidWorksLocal.exe: $($_.Exception.Message)" }
        requested_at_utc = $requestedAtUtc
        completed_at_utc = [DateTime]::UtcNow.ToString('o')
        bridge_version = $BridgeVersion
    }) $ExitBridgeError $safeRequestId
}

$finishedInTime = $proc.WaitForExit($timeoutMs)

if (-not $finishedInTime) {
    # We do not know whether the SOLIDWORKS-side operation completed,
    # partially applied, or did nothing -- reporting anything but UNKNOWN
    # here would be a guess dressed up as a fact. We stop only OUR OWN
    # worker process (SolidWorksLocal.exe), a helper this very script
    # started for this very call, so a later call cannot pile onto the
    # same stuck COM session. We never touch SOLIDWORKS.exe, Codex,
    # ChatGPT, or any process this script did not itself start.
    try { if (-not $proc.HasExited) { $proc.Kill() } } catch { }
    try { $proc.WaitForExit(5000) } catch { }

    $quarantineInfo = [ordered]@{
        quarantined_at_utc = [DateTime]::UtcNow.ToString('o')
        reason = 'TIMEOUT'
        request_id = $requestId
        tool = $tool
        timeout_ms = $timeoutMs
        message = 'A call to this tool did not finish within its timeout. The true SOLIDWORKS-side effect ' +
            '(completed, partially applied, or nothing) is not known. New write-capable calls are refused ' +
            'until a human confirms SOLIDWORKS state and calls this bridge once with tool=bridge_clear_quarantine.'
    }
    try { Write-JsonAtomic $quarantinePath $quarantineInfo } catch { }

    Exit-WithResponse ([ordered]@{
        ok = $false
        status = 'UNKNOWN'
        request_id = $requestId
        request_id_source = $requestIdSource
        tool = $tool
        arguments = $arguments
        error = [ordered]@{
            code = 'TIMEOUT'
            message = "The worker did not finish within $timeoutMs ms. This script's own helper process was stopped so a later call cannot collide with it, but whether the SOLIDWORKS operation itself completed, partially applied, or did nothing is NOT known -- this is not a claim that anything was cancelled or rolled back. The bridge is now quarantined for write-capable calls until a human confirms SOLIDWORKS state and clears it (tool=bridge_clear_quarantine)."
        }
        timeout_ms = $timeoutMs
        requested_at_utc = $requestedAtUtc
        completed_at_utc = [DateTime]::UtcNow.ToString('o')
        bridge_version = $BridgeVersion
    }) $ExitBridgeError $safeRequestId
}

# The timed WaitForExit above returned true, so the process has exited, but
# the async OutputDataReceived/ErrorDataReceived handlers may not all have
# fired yet. The documented, deterministic fix is to call the parameterless
# WaitForExit() -- for an already-exited process this returns immediately
# once redirected-stream draining is complete, with no arbitrary sleep guess.
$proc.WaitForExit()

$exitCode = $proc.ExitCode
$rawOutput = $stdoutTask.GetAwaiter().GetResult().Trim()
$rawStderr = $stderrTask.GetAwaiter().GetResult().Trim()

if ($rawStderr) {
    [IO.File]::WriteAllText($diagPath, $rawStderr, (New-Object Text.UTF8Encoding($false)))
} elseif (Test-Path -LiteralPath $diagPath) {
    Remove-Item -LiteralPath $diagPath -Force -ErrorAction SilentlyContinue
}

$parsedResult = $null
$parseError = $null
if ([string]::IsNullOrWhiteSpace($rawOutput)) {
    $parseError = 'Worker produced no stdout.'
} else {
    try { $parsedResult = $rawOutput | ConvertFrom-Json -ErrorAction Stop }
    catch { $parseError = $_.Exception.Message }
}

$wellFormed = ($null -ne $parsedResult) -and
    ($parsedResult.PSObject.Properties.Name -contains 'ok') -and
    ($parsedResult.ok -is [bool])
$toolOk = $wellFormed -and ($exitCode -eq 0) -and ($parsedResult.ok -eq $true)

if (-not $wellFormed -and $ReadOnlyTools -notcontains $tool) {
    Write-JsonAtomic $quarantinePath ([ordered]@{ reason='MALFORMED_WORKER_RESULT'; request_id=$requestId; tool=$tool })
}
$response = [ordered]@{
    ok = $toolOk
    status = if ($toolOk) { 'OK' } elseif ($wellFormed) { 'TOOL_FAILED' } else { 'BRIDGE_ERROR' }
    request_id = $requestId
    request_id_source = $requestIdSource
    tool = $tool
    arguments = $arguments
    worker_exit_code = $exitCode
    timeout_ms = $timeoutMs
    quarantine_active = $quarantineActive
    requested_at_utc = $requestedAtUtc
    completed_at_utc = [DateTime]::UtcNow.ToString('o')
    bridge_version = $BridgeVersion
}
if ($wellFormed) {
    $response.result = $parsedResult
} else {
    $response.raw_output = $rawOutput
    $response.parse_error = $parseError
    if ($rawStderr) { $response.stderr_excerpt = $rawStderr.Substring(0, [Math]::Min(2000, $rawStderr.Length)) }
}

$finalCode = if ($toolOk) { $ExitSuccess } elseif ($wellFormed) { $ExitToolFailed } else { $ExitBridgeError }
Exit-WithResponse $response $finalCode $safeRequestId
