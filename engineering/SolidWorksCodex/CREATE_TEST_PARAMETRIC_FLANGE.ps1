$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$partName = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('0KTQu9Cw0L3QtdGGINC90LDRgNGD0LbQvdC40Lk='))

$partPlan = [ordered]@{
    plan_version = '2'
    outer_profile = [ordered]@{
        type = 'circle'
        diameter_mm = 220
    }
    thickness_mm = 3
    circular_hole_pattern = [ordered]@{
        pitch_circle_diameter_mm = 178
        hole_diameter_mm = 17
        hole_count = 3
        start_angle_deg = 90
    }
    properties = [ordered]@{
        designation = '25.SHT.G.00.00.00.05'
        name = $partName
    }
    material = 'AISI 304'
}

$json = $partPlan | ConvertTo-Json -Depth 8 -Compress
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
Write-Host 'Creating a NEW parameter-driven flange from prismatic Plan v2:'
Write-Host 'outer D220 x 3 mm; three D17 holes on PCD 178; first hole at 90 degrees.'
Write-Host 'Material AISI 304 plus designation/name and creation parameters will be written and read back.'
Write-Host 'Existing documents will not be saved or edited.'
Write-Host ''
$raw = (& $exe --worker sw_create_part_from_plan $payload 2>&1 | Out-String).Trim()
Write-Host $raw
$result = $raw | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $result.ok) { throw 'SOLIDWORKS parameter-driven flange creation failed.' }
$path = [string]$result.data.file_path
if (-not (Test-Path -LiteralPath $path)) { throw "The connector reported success but the file does not exist: $path" }
if ([string]$result.data.verification.status -ne 'PASS') { throw 'Generated volume was not verified.' }
$topology = $result.data.verification.topology
if ([string]$topology.status -ne 'PASS') { throw 'Generated analytic cylinders were not verified.' }
if (-not [bool]$topology.outer_circle.analytic_cylindrical_surface_confirmed) {
    throw 'The D220 outer profile is not an analytic cylindrical surface.'
}
$diameters = @($topology.actual_diameters_mm)
$outerCount = @($diameters | Where-Object { [Math]::Abs(([double]$_) - 220.0) -le 0.001 }).Count
$holeCount = @($diameters | Where-Object { [Math]::Abs(([double]$_) - 17.0) -le 0.001 }).Count
if ($outerCount -ne 1 -or $holeCount -ne 3) { throw 'Expected one D220 cylinder and three D17 cylinders.' }
$holes = @($result.data.plan.holes)
if ($holes.Count -ne 3) { throw 'The connector did not resolve exactly three pattern holes.' }
if ([Math]::Abs([double]$holes[0].x_mm) -gt 0.000001 -or [Math]::Abs(([double]$holes[0].y_mm) - 89.0) -gt 0.000001) {
    throw 'The first pattern hole is not at the required top position (0, 89).'
}
$materialOk = [bool]$result.data.material_assigned -and [bool]$result.data.material.verified -and ([string]$result.data.material.name -eq 'AISI 304')
if (-not $materialOk) { throw 'AISI 304 was not assigned and verified.' }
$written = @($result.data.written_properties.items)
if ($written.Count -lt 9) { throw 'Designation, name or creation parameters were not all confirmed.' }
Write-Host ''
Write-Host 'PASS: D220 flange, 3-hole pattern, AISI 304, properties, volume and analytic circles passed.' -ForegroundColor Green
Start-Process explorer.exe -ArgumentList "/select,`"$path`""
Read-Host 'Press Enter to close'
