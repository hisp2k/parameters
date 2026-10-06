$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$report = Join-Path $root '_profile_parts_2_5_live_report.txt'
if (Test-Path -LiteralPath $report) { Remove-Item -LiteralPath $report -Force }

function Log([string]$text) { Add-Content -LiteralPath $report -Value $text -Encoding UTF8 }

function Run-Plan([string]$label, [string]$relativePlan, [int]$expectedCylinders) {
    Log ("===== " + $label + " =====")
    $path = Join-Path $root $relativePlan
    $documentJson = [IO.File]::ReadAllText($path, [Text.Encoding]::UTF8)
    $document = $documentJson | ConvertFrom-Json
    $json = $document.plan | ConvertTo-Json -Depth 20 -Compress
    $payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
    $raw = (& $exe --worker sw_create_profile_part_from_plan $payload 2>&1 |
        ForEach-Object { $_.ToString() }) -join "`n"
    Log $raw
    $result = $raw | ConvertFrom-Json
    if (-not $result.ok) {
        throw ($label + ': ' + [string]$result.error.code + ': ' + [string]$result.error.message)
    }
    $data = $result.data
    if ([string]$data.connector_version -ne '2.5.0') {
        throw ($label + ': expected connector 2.5.0; run BUILD.cmd first')
    }
    if (-not (Test-Path -LiteralPath ([string]$data.file_path))) {
        throw ($label + ': output file not found')
    }
    if ([string]$data.verification.status -ne 'PASS') {
        throw ($label + ': geometry verification failed')
    }
    if ([string]$data.verification.topology.status -ne 'PASS') {
        throw ($label + ': topology verification failed')
    }
    if ([int]$data.verification.topology.solid_body_count -ne 1) {
        throw ($label + ': expected one solid body')
    }
    if ([int]$data.verification.topology.expected_cylindrical_face_count -ne $expectedCylinders) {
        throw ($label + ': unexpected analytic cylinder count')
    }
    $expectedVolume = [double]$document.expected_volume_m3
    $actualVolume = [double]$data.verification.actual_volume_m3
    if ([Math]::Abs($actualVolume - $expectedVolume) / $expectedVolume -ge 0.001) {
        throw ($label + ': final CAD volume differs from independent fixture by 0.1% or more')
    }
    Log ("PASS: " + [string]$data.file_path)
    Log ''
}

try {
    $sw = @(Get-Process -Name SLDWORKS -ErrorAction SilentlyContinue)
    if ($sw.Count -ne 1) { throw 'Start exactly one SOLIDWORKS 2026 instance before this test.' }
    if (-not (Test-Path -LiteralPath $exe)) { throw 'SolidWorksLocal.exe not found. Run BUILD.cmd first.' }

    Run-Plan 'RECTANGULAR TUBE WITH ROUND CORNERS AND HOLES' `
        'drawing-plans\control_profile_rectangular_tube_v2.json' 12
    Run-Plan 'ROUND TUBE' `
        'drawing-plans\control_profile_round_tube_v2.json' 2
    Run-Plan 'RECTANGULAR TUBE WITH AXIAL OBROUND SLOTS' `
        'drawing-plans\control_profile_slots_v3.json' 16

    Log 'RESULT: PASS - all ProfilePartPlan v2/v3 control models were created and independently verified.'
}
catch {
    Log ('RESULT: FAIL - ' + $_.Exception.Message)
    throw
}
finally {
    Log 'manufacturing_approved=false'
}
