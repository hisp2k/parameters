$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$reportPath = Join-Path $root '_claude_diag_profile_length_report.txt'
if (Test-Path -LiteralPath $reportPath) { Remove-Item -LiteralPath $reportPath -Force }
function Log($text) { Add-Content -LiteralPath $reportPath -Value $text -Encoding UTF8 }

# DIAGNOSTIC ONLY (not a mandated test artifact): isolate whether CUT_FAILED on the
# real 05.SHT.TR.11.00.00.05 plan (4000 mm, 50x50x4 mm, dia 9 mm hole at edge_offset 32 mm)
# is caused by the very long/thin extrusion (4000/50 = 80:1) or by the hole parameters
# themselves. Same cross-section, thickness, diameter and edge_offset as the real plan,
# but only 500 mm long (7:1 aspect ratio) and only the first two leg_a hole positions
# (415, 475 mm) which both fit inside 500 mm. No leg_b holes, to isolate the mechanism.
$plan = [ordered]@{
    plan_version   = '1'
    cross_section  = [ordered]@{ type = 'equal_angle'; leg_a_mm = [double]50; leg_b_mm = [double]50; thickness_mm = [double]4 }
    length_mm      = [double]500
    material       = 'AISI 304'
    properties     = [ordered]@{ designation = 'DIAG_LENGTH_TEST_500'; name = 'Diag' }
    hole_groups    = @(
        [ordered]@{ face = 'leg_a'; pattern = 'explicit'; diameter_mm = [double]9; edge_offset_mm = [double]32; positions_mm = @([double]415, [double]475); count = 2 }
    )
}

try {
    Log 'DIAGNOSTIC: same cross-section/thickness/diameter/edge_offset as the real 05.SHT.TR.11.00.00.05 plan, but length_mm=500 (not 4000) and only the first two leg_a holes.'
    Log 'Purpose: isolate whether CUT_FAILED on the real plan is caused by the 4000 mm / 80:1 aspect-ratio extrusion, or by the hole geometry itself.'
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
        Log 'RESULT: FAIL - tool call did not return ok=true (see raw JSON above).'
    } else {
        Log ("RESULT: PASS - status=" + $result.data.verification.status + ", solid_body_count=" + $result.data.verification.topology.solid_body_count)
    }
}
catch {
    Log ("UNHANDLED EXCEPTION: " + $_.ToString())
}
Add-Content -LiteralPath $reportPath -Value 'DONE' -Encoding UTF8
