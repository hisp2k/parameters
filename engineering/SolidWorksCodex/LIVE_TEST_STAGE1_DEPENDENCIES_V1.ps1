$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
. (Join-Path $repo 'DependencyGraph.ps1')
Set-Location $repo
$exe = Join-Path $repo 'SolidWorksLocal.exe'
$reportPath = Join-Path $repo '_claude_live_test_stage1_dependencies_report.txt'
if (Test-Path -LiteralPath $reportPath) { Remove-Item -LiteralPath $reportPath -Force }
function Log($text) { Add-Content -LiteralPath $reportPath -Value $text -Encoding UTF8 }

# Stage 1: confirm that 25.SHT.G.00.00.00.00 SB Transporter.SLDASM is genuinely the root
# assembly of the pilot project folder via real API dependency references from
# ISldWorks.GetDocumentDependencies2 (sw_document_dependencies), not by filename or the
# 00.00.00.00 / 01.xx numbering convention alone.
#
# GetDocumentDependencies2 only reports DOWNWARD references (what a file itself needs to
# open), never upward ("used by") references - SOLIDWORKS does not store those in the file
# at all. So "is file X used as a sub-component of some other file Y in this folder" can
# only be answered by asking every OTHER candidate file Y for ITS OWN dependency list and
# checking whether X appears in it.
#
# v1 of this script assumed GetDocumentDependencies2 returns the full transitive closure
# (every file reachable at any depth) and required every *.SLDASM sibling in the folder to
# appear DIRECTLY in the target's own list. A first live run showed that assumption was
# wrong: three files that sit two levels deep in the numbering convention (e.g.
# 25.SHT.G.01.01.00.00, a child of 25.SHT.G.01.00.00.00, not of the root) were NOT in the
# root's own dependency list, even though the root clearly does contain them (they are real
# components of the built assembly, confirmed by sw_assembly_tree in the original Stage 0
# live test - 495 total instances, 372 top-level). The most likely explanation, based only
# on what was actually observed, is that GetDocumentDependencies2 reports direct/one-level
# references, not a recursive transitive closure - but this script does not assert that as
# fact, it only uses graph reachability so the conclusion holds either way.
#
# Two-directional check, scoped to the *.SLDASM files directly inside the pilot folder:
#   A) every sibling assembly must be REACHABLE from the target by following directed
#      "X references Y" edges built only from what GetDocumentDependencies2 actually
#      returned for each of the 13 files (target + 12 siblings) - directly, or through one
#      or more intermediate siblings. This does not assume any particular depth behaviour
#      of the API; it only requires that the observed edges connect target to every sibling.
#   B) none of the sibling assemblies' own dependency lists may include the target path
#      (no candidate file in this folder uses the target as a sub-component).
# This does NOT prove no assembly anywhere else on disk references the target; it proves
# only that within this project folder, the target is not a sub-component of any other
# assembly file present, and that every other assembly file present is reachable from it.
#
# sw_document_dependencies never opens the file as the active document, so this test does
# not touch SOLIDWORKS document state at all - only the live API/process pre-check applies.

function Get-SolidWorksProcesses { @(Get-Process -Name 'SLDWORKS' -ErrorAction SilentlyContinue) }

$swProcs = Get-SolidWorksProcesses
if ($swProcs.Count -eq 0) {
    Log 'SOLIDWORKS_NOT_RUNNING: start SOLIDWORKS and re-run.'
    Add-Content -LiteralPath $reportPath -Value 'ALL DONE (aborted before any worker call)' -Encoding UTF8
    exit 3
}
if ($swProcs.Count -gt 1) {
    Log ('MULTIPLE_SOLIDWORKS: found ' + $swProcs.Count + ' SLDWORKS.exe processes. Leave exactly one running.')
    Add-Content -LiteralPath $reportPath -Value 'ALL DONE (aborted before any worker call)' -Encoding UTF8
    exit 3
}
Log ('Pre-check OK: exactly one SLDWORKS.exe running, pid=' + $swProcs[0].Id)
Log ''

$pilotFolder = Join-Path $repo '25.SHT.G.00.00.00.00 СБ'
$targetPath = Join-Path $pilotFolder '25.SHT.G.00.00.00.00 СБ  Транспортер.SLDASM'
if (-not (Test-Path -LiteralPath $targetPath)) {
    Log ('ABORT: target assembly not found on disk: ' + $targetPath)
    Add-Content -LiteralPath $reportPath -Value 'ALL DONE (aborted, target missing)' -Encoding UTF8
    exit 3
}

$allAssemblies = @(Get-ChildItem -LiteralPath $pilotFolder -Filter '*.SLDASM' -File | Where-Object { $_.Name -notmatch '^~\$' })
$siblings = @($allAssemblies | Where-Object { $_.FullName -ne $targetPath })
$targetName = ([IO.Path]::GetFileName($targetPath))
Log ('Target assembly: ' + $targetPath)
Log ('SLDASM files found directly in pilot folder (excluding lock files): ' + $allAssemblies.Count + ' total, ' + $siblings.Count + ' other than target.')
foreach ($s in $siblings) { Log ('  candidate: ' + $s.Name) }
Log ''

$perCallTimeoutMs = 90000
$global:AnyFail = $false

function Invoke-Worker([string]$tool, [hashtable]$callArgs, [string]$label) {
    $requestId = [guid]::NewGuid().ToString('N')
    Log ('===== ' + $label + ' =====')
    Log ('request_id=' + $requestId + ' tool=' + $tool + ' args=' + ($callArgs | ConvertTo-Json -Depth 10 -Compress))
    $startUtc = [DateTime]::UtcNow
    $json = $callArgs | ConvertTo-Json -Depth 20 -Compress
    $payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
    $stdOutFile = Join-Path $repo ('_claude_live_test_' + $requestId + '.out.txt')
    $stdErrFile = Join-Path $repo ('_claude_live_test_' + $requestId + '.err.txt')
    $psi = @{
        FilePath               = $exe
        ArgumentList            = @('--worker', $tool, $payload)
        WorkingDirectory       = $repo
        PassThru               = $true
        NoNewWindow            = $true
        RedirectStandardOutput = $stdOutFile
        RedirectStandardError  = $stdErrFile
    }
    $proc = Start-Process @psi
    $finished = $proc.WaitForExit($perCallTimeoutMs)
    $endUtc = [DateTime]::UtcNow
    if (-not $finished) {
        try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch { }
        Log ('RESULT: TIMEOUT after ' + $perCallTimeoutMs + ' ms - worker (pid=' + $proc.Id + ') killed. SOLIDWORKS was NOT touched.')
        Log ''
        $global:AnyFail = $true
        return $null
    }
    $raw = ''
    if (Test-Path -LiteralPath $stdOutFile) { $raw = (Get-Content -LiteralPath $stdOutFile -Raw -Encoding UTF8) }
    $errText = ''
    if (Test-Path -LiteralPath $stdErrFile) { $errText = (Get-Content -LiteralPath $stdErrFile -Raw -Encoding UTF8) }
    Remove-Item -LiteralPath $stdOutFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $stdErrFile -Force -ErrorAction SilentlyContinue
    Log ('exit_code=' + $proc.ExitCode + ' duration_ms=' + [long](($endUtc - $startUtc).TotalMilliseconds))
    if ($errText) { Log ('STDERR: ' + $errText) }
    $result = $null
    try { $result = $raw | ConvertFrom-Json } catch { Log ('JSON PARSE FAILED: ' + $_); Log ('RAW: ' + $raw) }
    if ($null -eq $result -or -not $result.ok) {
        $code = $null
        if ($result -and $result.error) { $code = [string]$result.error.code }
        Log ('RESULT: FAIL - tool call did not return ok=true.' + $(if ($code) { ' code=' + $code } else { '' }))
        Log ('RAW: ' + $raw)
        $global:AnyFail = $true
        return $null
    }
    Log 'RESULT: OK'
    Log ''
    return $result
}

# ---- Collect each of the 13 files' own dependency set (one call per file) ----
$depByPath = @{}
$callFailures = New-Object System.Collections.Generic.List[string]

$targetDep = Invoke-Worker 'sw_document_dependencies' @{ file_path = $targetPath } 'Target dependencies (downward references of the root candidate)'
if ($null -eq $targetDep -or $targetDep.data.api_call_status -ne 'OK') {
    Log 'ABORT: could not read target dependencies (call failed or api_call_status != OK), cannot continue.'
    Add-Content -LiteralPath $reportPath -Value 'ALL DONE (aborted, target dependency read failed)' -Encoding UTF8
    exit 4
}
Log ('CHECK: target api_call_status = ' + $targetDep.data.api_call_status + ', dependency_count = ' + $targetDep.data.dependency_count)
$targetKey = Get-DependencyPathKey $targetPath
$depByPath[$targetKey] = Get-DependencyPaths $targetDep
Log ''

$i = 0
foreach ($s in $siblings) {
    $i++
    $r = Invoke-Worker 'sw_document_dependencies' @{ file_path = $s.FullName } ('Sibling ' + $i + '/' + $siblings.Count + ' dependencies: ' + $s.Name)
    if ($null -eq $r) { $callFailures.Add($s.Name); continue }
    if ($r.data.api_call_status -ne 'OK') { $callFailures.Add($s.Name + ' (api_call_status=' + $r.data.api_call_status + ')'); continue }
    Log ('  ' + $s.Name + ': dependency_count=' + $r.data.dependency_count)
    $depByPath[(Get-DependencyPathKey $s.FullName)] = Get-DependencyPaths $r
}
Log ''
if ($callFailures.Count -gt 0) {
    Log ('FAIL: ' + $callFailures.Count + ' dependency call(s) did not succeed: ' + ($callFailures -join '; '))
    $global:AnyFail = $true
} else {
    Log ('PASS: all ' + $allAssemblies.Count + ' dependency calls (target + ' + $siblings.Count + ' siblings) returned api_call_status=OK.')
}
Log ''

# ---- Step A: every sibling must be reachable from target via observed reference edges ----
# Follow only normalized full-path references within the candidate set.
$visited = Get-ReachableDependencyPaths $depByPath $targetPath
$directHits = New-Object System.Collections.Generic.List[string]
$indirectHits = New-Object System.Collections.Generic.List[string]
$unreachable = New-Object System.Collections.Generic.List[string]
foreach ($s in $siblings) {
    $key = Get-DependencyPathKey $s.FullName
    $direct = $depByPath.ContainsKey($targetKey) -and $depByPath[$targetKey].Contains($key)
    if ($direct) { $directHits.Add($s.Name) }
    elseif ($visited.Contains($key)) { $indirectHits.Add($s.Name) }
    else { $unreachable.Add($s.Name) }
}
Log ('CHECK: ' + $directHits.Count + ' sibling(s) directly in target''s own dependency list: ' + (($directHits -join '; ')))
Log ('CHECK: ' + $indirectHits.Count + ' sibling(s) reachable only through an intermediate sibling (not directly in target''s list - observed evidence that GetDocumentDependencies2 does not always report the full transitive closure): ' + (($indirectHits -join '; ')))
if ($unreachable.Count -eq 0) {
    Log ('PASS: all ' + $siblings.Count + ' sibling assembly files are reachable from the target by following only the reference edges actually observed from the live API (direct or indirect).')
} else {
    Log ('FAIL: ' + $unreachable.Count + ' sibling assembly file(s) are NOT reachable from the target through any observed reference chain: ' + ($unreachable -join '; ') + ' - this is real evidence against treating the target as their ancestor, not an artifact of API depth.')
    $global:AnyFail = $true
}
Log ''

# ---- Step B: none of the siblings' own dependency lists may include the target ----
$siblingsReferencingTarget = New-Object System.Collections.Generic.List[string]
foreach ($s in $siblings) {
    $key = Get-DependencyPathKey $s.FullName
    if ($depByPath.ContainsKey($key) -and $depByPath[$key].Contains($targetKey)) { $siblingsReferencingTarget.Add($s.Name) }
}
if ($siblingsReferencingTarget.Count -eq 0) {
    Log ('PASS: none of the ' + $siblings.Count + ' candidate assembly files in the pilot folder reference the target as a dependency (target is not a sub-component of any of them).')
} else {
    Log ('FAIL: the target assembly WAS found in the dependency list of: ' + ($siblingsReferencingTarget -join '; ') + ' - the target may not be the root assembly.')
    $global:AnyFail = $true
}
Log ''

Log '===== Scope note ====='
Log 'This verifies root status only relative to the *.SLDASM files physically present in this one pilot project folder. It does not and cannot prove no assembly elsewhere on disk references the target, since GetDocumentDependencies2 only exposes downward (what-this-file-needs) references, never upward (who-uses-this-file) references - there is no SOLIDWORKS API to ask that question directly for an arbitrary unknown file. The reachability check in Step A only uses edges actually observed from the live API for these 13 files; it does not assume GetDocumentDependencies2 returns a full transitive closure. Combined with Step B (no sibling references the target), this is the strongest evidence obtainable from this API within this folder.'
Log ''

Log ('OVERALL: ' + $(if ($global:AnyFail) { 'FAIL - see above' } else { 'ALL CHECKS PASSED' }))
Add-Content -LiteralPath $reportPath -Value 'ALL DONE' -Encoding UTF8
if ($global:AnyFail) { exit 1 }
