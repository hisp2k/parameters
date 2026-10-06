$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$partName = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('0JrQvtC90LXRhiDQstCw0LvQsA=='))

$outer = @(
    [ordered]@{ x_mm = 0;             diameter_mm = 152 },
    [ordered]@{ x_mm = 4;             diameter_mm = 160 },
    [ordered]@{ x_mm = 160;           diameter_mm = 160 },
    [ordered]@{ x_mm = 160;           diameter_mm = 172 },
    [ordered]@{ x_mm = 164.663076582; diameter_mm = 192 },
    [ordered]@{ x_mm = 175;           diameter_mm = 192 },
    [ordered]@{ x_mm = 179;           diameter_mm = 200 },
    [ordered]@{ x_mm = 187;           diameter_mm = 200 },
    [ordered]@{ x_mm = 187;           diameter_mm = 180 },
    [ordered]@{ x_mm = 197;           diameter_mm = 180 },
    [ordered]@{ x_mm = 197;           diameter_mm = 192 },
    [ordered]@{ x_mm = 384;           diameter_mm = 192 },
    [ordered]@{ x_mm = 390;           diameter_mm = 180 },
    [ordered]@{ x_mm = 443;           diameter_mm = 180 },
    [ordered]@{ x_mm = 443;           diameter_mm = 172 },
    [ordered]@{ x_mm = 483;           diameter_mm = 172 },
    [ordered]@{ x_mm = 483;           diameter_mm = 163.2 },
    [ordered]@{ x_mm = 483.121792748; diameter_mm = 161.975413018 },
    [ordered]@{ x_mm = 483.468629150; diameter_mm = 160.937258300 },
    [ordered]@{ x_mm = 483.987706509; diameter_mm = 160.243585496 },
    [ordered]@{ x_mm = 484.6;         diameter_mm = 160 },
    [ordered]@{ x_mm = 543;           diameter_mm = 160 },
    [ordered]@{ x_mm = 543;           diameter_mm = 155 },
    [ordered]@{ x_mm = 546.4;         diameter_mm = 155 },
    [ordered]@{ x_mm = 546.4;         diameter_mm = 160 },
    [ordered]@{ x_mm = 550;           diameter_mm = 160 },
    [ordered]@{ x_mm = 560;           diameter_mm = 140 }
)
$partPlan = [ordered]@{
    plan_version = '3'
    outer_profile = $outer
    spline_zone = [ordered]@{
        start_x_mm = 197
        tip_end_x_mm = 384
        end_x_mm = 390
        root_diameter_mm = 180
        tip_diameter_mm = 192
        tooth_count = 12
        tooth_width_mm = 25
        phase_angle_deg = 0
    }
    properties = [ordered]@{
        designation = 'WRM.02.02.00.003'
        name = $partName
    }
    reference_volume_mm3 = 13312804.679783953
}

$json = $partPlan | ConvertTo-Json -Depth 8 -Compress
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
Write-Host 'Creating a NEW splined shaft-end test part from turned Plan v3:'
Write-Host '560 mm long; D200 maximum; twelve straight external splines; axial spline-end taper.'
Write-Host 'Reference STEP volume: 13312804.679783953 mm3. Existing documents will not be saved or edited.'
Write-Host ''
$raw = (& $exe --worker sw_create_turned_part_from_plan $payload 2>&1 | Out-String).Trim()
Write-Host $raw
$result = $raw | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $result.ok) { throw 'SOLIDWORKS splined-shaft creation failed.' }
$path = [string]$result.data.file_path
if (-not (Test-Path -LiteralPath $path)) { throw "The connector reported success but the file does not exist: $path" }
if ([string]$result.data.verification.status -ne 'PASS') { throw 'Generated splined-shaft geometry was not verified.' }
$referenceError = [double]$result.data.verification.reference_relative_error
if ($referenceError -gt 0.0005) { throw "Reference-volume error is too high: $referenceError" }
if ([int]$result.data.features.longitudinal_spline_count -ne 12) { throw 'The connector did not confirm twelve splines.' }
$written = @($result.data.features.properties_written.items)
if ($written.Count -ne 2) { throw 'The connector did not confirm designation and name properties.' }
$box = @($result.data.verification.approximate_bbox_xyz_mm)
if ($box.Count -ne 3) { throw 'The connector did not return a three-axis bounding box.' }
Write-Host ''
Write-Host 'PASS: splined shaft-end SLDPRT exists; 12 splines, properties and STEP reference volume passed.' -ForegroundColor Green
Start-Process explorer.exe -ArgumentList "/select,`"$path`""
Read-Host 'Press Enter to close'
