$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$reportPath = Join-Path $root '_claude_profile_realpdf_test_report.txt'
if (Test-Path -LiteralPath $reportPath) { Remove-Item -LiteralPath $reportPath -Force }
function Log($text) { Add-Content -LiteralPath $reportPath -Value $text -Encoding UTF8 }

# "Уголок" (angle), base64 to avoid file-encoding issues.
$name = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('0KPQs9C+0LvQvtC6'))

# Plan taken verbatim from drawing-plans/05.SHT.TR.11.00.00.05.json (real PDF:
# "05.SHT.TR.11.00.00.05 Уголок.pdf", sha256 4b9ea093c3275dec6d1eab9275eef8e63047ba5848b05308450a8849dd03bb08).
# NOTE: the disclosed construction assumption from that file applies here too --
# both edge offsets (32 mm on leg_a, 24 mm on leg_b) are built from the edge of
# each leg adjoining the inner corner (heel), because the drawing's two separate
# orthogonal views do not unambiguously fix which physical edge is meant. This is
# a construction assumption only, not a proven fact, and needs designer
# confirmation before manufacturing -- consistent with manufacturing_approved=false.
$plan = [ordered]@{
    plan_version   = '1'
    cross_section  = [ordered]@{ type = 'equal_angle'; leg_a_mm = [double]50; leg_b_mm = [double]50; thickness_mm = [double]4 }
    length_mm      = [double]4000
    material       = 'AISI 304'
    properties     = [ordered]@{ designation = '05.SHT.TR.11.00.00.05'; name = $name }
    hole_groups    = @(
        [ordered]@{
            face = 'leg_a'; pattern = 'explicit'; diameter_mm = [double]9; edge_offset_mm = [double]32
            positions_mm = @([double]415, [double]475, [double]975, [double]1035, [double]2915, [double]2975, [double]3437, [double]3497)
            count = 8
        },
        [ordered]@{ face = 'leg_b'; pattern = 'linear'; diameter_mm = [double]9; edge_offset_mm = [double]24; start_mm = [double]100; count = 20; pitch_mm = [double]200 }
    )
}

try {
    Log 'PROFILE-PART REAL-PDF TEST: 05.SHT.TR.11.00.00.05 "Уголок" -- 50x50x4 mm equal angle, 4000 mm long, 8 (leg_a, explicit) + 20 (leg_b, linear) holes.'
    Log 'A new part will be created in local Workspace from this plan. Existing documents will not be saved or edited.'
    Log 'Source PDF sha256: 4b9ea093c3275dec6d1eab9275eef8e63047ba5848b05308450a8849dd03bb08'
    Log 'Disclosed construction assumption: both edge offsets measured from the heel (inner-corner) edge of each leg -- unconfirmed by the drawing views, requires designer review before manufacturing.'
    Log ''
    $json = $plan | ConvertTo-Json -Depth 14 -Compress
    Log ("REQUEST JSON: " + $json)
    Log ''
    $payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
    $raw = $null
    try { $raw = (& $exe --worker sw_create_profile_part_from_plan $payload 2>&1 | ForEach-Object { $_.ToString() }) -join "`n" }
    catch { $raw = "EXCEPTION DURING WORKER CALL: $_" }
    Log 'RAW RESPONSE:'
    Log $raw
    Log ''

    $result = $null
    try { $result = $raw | ConvertFrom-Json } catch { Log ("JSON PARSE FAILED: " + $_) }

    if ($null -eq $result -or -not $result.ok) {
        Log 'RESULT: FAIL - tool call did not return ok=true.'
    }
    else {
        $data = $result.data
        $path = [string]$data.file_path
        $topology = $data.verification.topology
        $diam = @($topology.actual_diameters_mm) | Sort-Object
        $envelope = @($data.plan.calculated.envelope_xyz_mm)
        $expectedVol = 0.0015288748678616584

        $allNine = $true
        foreach ($d in $diam) { if ([Math]::Abs(([double]$d) - 9) -gt 0.01) { $allNine = $false } }

        $checks = [ordered]@{
            'connector_version == 2.2.2'         = ([string]$data.connector_version -eq '2.2.2')
            'output file exists'                 = (Test-Path -LiteralPath $path)
            'verification.status == PASS'        = ([string]$data.verification.status -eq 'PASS')
            'topology.status == PASS'            = ([string]$topology.status -eq 'PASS')
            'solid_body_count == 1'              = ([int]$topology.solid_body_count -eq 1)
            'expected_cylindrical_face_count == 28' = ([int]$topology.expected_cylindrical_face_count -eq 28)
            'actual_cylindrical_face_count == 28' = ([int]$topology.actual_cylindrical_face_count -eq 28)
            'all 28 diameters == 9 mm'           = ($diam.Count -eq 28 -and $allNine)
            'envelope == 4000 x 50 x 50 mm'      = ($envelope.Count -eq 3 -and [Math]::Abs(([double]$envelope[0]) - 4000) -lt 0.01 -and [Math]::Abs(([double]$envelope[1]) - 50) -lt 0.01 -and [Math]::Abs(([double]$envelope[2]) - 50) -lt 0.01)
            'actual_volume within 0.1% of expected' = ([Math]::Abs(([double]$data.verification.actual_volume_m3) - $expectedVol) / $expectedVol -lt 0.001)
        }

        Log ("file_path: " + $path)
        foreach ($key in $checks.Keys) { Log ("  [" + $(if ($checks[$key]) { "OK" } else { "FAIL" }) + "] " + $key) }
        $failCount = ($checks.Values | Where-Object { -not $_ }).Count
        Log ''
        if ($failCount -eq 0) {
            Log 'RESULT: PASS - real-PDF-derived profile part created; volume and B-rep topology verification match the plan; envelope and hole diameters as expected.'
            Log 'REMINDER: this only proves the analytic checks (volume, hole count/diameters, one solid body). It does NOT confirm the heel/toe edge-offset assumption or which physical leg each hole group landed on -- that requires visual/caliper confirmation by a designer in SOLIDWORKS before manufacturing_approved can ever be set to true.'
        }
        else {
            Log ("RESULT: FAIL - " + $failCount + " check(s) did not match. See raw JSON above.")
        }
    }
}
catch {
    Log ("UNHANDLED EXCEPTION: " + $_.ToString())
}
Add-Content -LiteralPath $reportPath -Value 'DONE' -Encoding UTF8
