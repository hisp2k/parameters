$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$reportPath = Join-Path $root '_claude_profile_control_test_report.txt'
if (Test-Path -LiteralPath $reportPath) { Remove-Item -LiteralPath $reportPath -Force }
function Log($text) { Add-Content -LiteralPath $reportPath -Value $text -Encoding UTF8 }

# "Контрольный уголок" (control angle), base64 to avoid file-encoding issues.
$name = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('0JrQvtC90YLRgNC+0LvRjNC90YvQuSDRg9Cz0L7Qu9C+0Lo='))

# Synthetic control plan for sw_create_profile_part_from_plan:
# 40 x 40 x 3 mm equal angle, 200 mm long.
# leg_a: linear group, 3 holes Ø6, pitch 60, start 40, edge_offset 20 -> positions 40/100/160.
# leg_b: explicit group, 1 hole Ø5 at 100 mm, edge_offset 15.
$plan = [ordered]@{
    plan_version   = '1'
    cross_section  = [ordered]@{ type = 'equal_angle'; leg_a_mm = [double]40; leg_b_mm = [double]40; thickness_mm = [double]3 }
    length_mm      = [double]200
    material       = 'AISI 304'
    properties     = [ordered]@{ designation = 'AI_CONTROL_PROFILE_ANGLE_01'; name = $name }
    hole_groups    = @(
        [ordered]@{ face = 'leg_a'; pattern = 'linear';   diameter_mm = [double]6; edge_offset_mm = [double]20; start_mm = [double]40; count = 3; pitch_mm = [double]60 },
        [ordered]@{ face = 'leg_b'; pattern = 'explicit'; diameter_mm = [double]5; edge_offset_mm = [double]15; positions_mm = @([double]100); count = 1 }
    )
}

try {
    Log 'PROFILE-PART CONTROL TEST: 40x40x3 mm equal angle, 200 mm long, linear (leg_a) + explicit (leg_b) hole groups.'
    Log 'A new control part will be created in local Workspace. Existing documents will not be saved or edited.'
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
        $expectedVol = 4.5886626132804425e-05

        $checks = [ordered]@{
            'connector_version == 2.2.2'        = ([string]$data.connector_version -eq '2.2.2')
            'output file exists'                = (Test-Path -LiteralPath $path)
            'verification.status == PASS'       = ([string]$data.verification.status -eq 'PASS')
            'topology.status == PASS'           = ([string]$topology.status -eq 'PASS')
            'solid_body_count == 1'             = ([int]$topology.solid_body_count -eq 1)
            'expected_cylindrical_face_count == 4' = ([int]$topology.expected_cylindrical_face_count -eq 4)
            'actual_cylindrical_face_count == 4' = ([int]$topology.actual_cylindrical_face_count -eq 4)
            'diameters == [5,6,6,6] mm'         = ($diam.Count -eq 4 -and [Math]::Abs($diam[0] - 5) -lt 0.01 -and [Math]::Abs($diam[1] - 6) -lt 0.01 -and [Math]::Abs($diam[2] - 6) -lt 0.01 -and [Math]::Abs($diam[3] - 6) -lt 0.01)
            'envelope == 200 x 40 x 40 mm'      = ($envelope.Count -eq 3 -and [Math]::Abs(([double]$envelope[0]) - 200) -lt 0.01 -and [Math]::Abs(([double]$envelope[1]) - 40) -lt 0.01 -and [Math]::Abs(([double]$envelope[2]) - 40) -lt 0.01)
            'actual_volume within 0.1% of expected' = ([Math]::Abs(([double]$data.verification.actual_volume_m3) - $expectedVol) / $expectedVol -lt 0.001)
        }

        Log ("file_path: " + $path)
        foreach ($key in $checks.Keys) { Log ("  [" + $(if ($checks[$key]) { "OK" } else { "FAIL" }) + "] " + $key) }
        $failCount = ($checks.Values | Where-Object { -not $_ }).Count
        Log ''
        if ($failCount -eq 0) {
            Log 'RESULT: PASS - control profile part created; volume and B-rep topology verification match the plan; envelope and hole diameters as expected.'
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
