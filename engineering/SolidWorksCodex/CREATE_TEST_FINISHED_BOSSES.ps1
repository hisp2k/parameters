$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$partName = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('0J/Qu9C40YLQsCDRgSDRhNCw0YHQutCw0LzQuCDQuCDRgdC60YDRg9Cz0LvQtdC90LjRj9C80Lg='))

$partPlan = [ordered]@{
    plan_version = '5'
    outer_profile = [ordered]@{
        type = 'rectangle'
        width_mm = 200
        height_mm = 120
    }
    thickness_mm = 12
    circular_pockets = @(
        [ordered]@{ x_mm = 0; y_mm = -18; diameter_mm = 20; depth_mm = 5 }
    )
    straight_slots = @(
        [ordered]@{ x1_mm = -30; y1_mm = -42; x2_mm = 30; y2_mm = -42; width_mm = 10; cut_type = 'through' }
    )
    rectangular_bosses = @(
        [ordered]@{
            x_mm = -55; y_mm = 25; width_mm = 54; height_mm = 34; extrusion_mm = 12
            corner_style = 'chamfer'; corner_size_mm = 5
        },
        [ordered]@{
            x_mm = 55; y_mm = 25; width_mm = 54; height_mm = 34; extrusion_mm = 16
            corner_style = 'round'; corner_size_mm = 7
        }
    )
    properties = [ordered]@{
        designation = 'AI.TEST.090'
        name = $partName
    }
    material = 'AISI 304'
}

$json = $partPlan | ConvertTo-Json -Depth 10 -Compress
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
Write-Host 'Creating a NEW Plan v5 control part: 200 x 120 x 12 mm base.'
Write-Host 'Left boss: 54 x 34 x 12, four 5 mm corner chamfers.'
Write-Host 'Right boss: 54 x 34 x 16, four R7 rounded corners.'
Write-Host 'Cuts: one D20 blind pocket and one D10 through slot.'
Write-Host 'Existing documents will not be saved or edited.'
Write-Host ''
$raw = (& $exe --worker sw_create_part_from_plan $payload 2>&1 | Out-String).Trim()
Write-Host $raw
$result = $raw | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $result.ok) { throw 'SOLIDWORKS Plan v5 finished-boss creation failed.' }
$path = [string]$result.data.file_path
if (-not (Test-Path -LiteralPath $path)) { throw "The connector reported success but the file does not exist: $path" }
if ([string]$result.data.connector_version -ne '2.2.2') { throw 'The installed connector is not version 2.2.2.' }
if ([string]$result.data.verification.status -ne 'PASS' -or
    [string]$result.data.verification.after_bosses.status -ne 'PASS') {
    throw 'Final volume or total volume after bosses was not verified.'
}
$bosses = @($result.data.verification.bosses)
if ($bosses.Count -ne 2 -or @($bosses | Where-Object { [string]$_.status -ne 'PASS' }).Count -ne 0) {
    throw 'Both finished bosses must pass their exact added-volume checks.'
}
$cuts = @($result.data.verification.cuts)
if ($cuts.Count -ne 2 -or @($cuts | Where-Object { [string]$_.status -ne 'PASS' }).Count -ne 0) {
    throw 'Both cuts must pass their exact removed-volume checks.'
}
$topology = $result.data.verification.topology
if ([string]$topology.status -ne 'PASS' -or [int]$topology.solid_body_count -ne 1) {
    throw 'The final result is not one verified solid body.'
}
$diameters = @($topology.actual_diameters_mm)
$slotCaps = @($diameters | Where-Object { [Math]::Abs(([double]$_) - 10.0) -le 0.001 }).Count
$roundedCorners = @($diameters | Where-Object { [Math]::Abs(([double]$_) - 14.0) -le 0.001 }).Count
$roundPocket = @($diameters | Where-Object { [Math]::Abs(([double]$_) - 20.0) -le 0.001 }).Count
if ($diameters.Count -ne 7 -or $slotCaps -ne 2 -or $roundedCorners -ne 4 -or $roundPocket -ne 1) {
    throw 'Expected four R7 corner cylinders, one D20 pocket and two D10 slot-end cylinders.'
}
$returnedBosses = @($result.data.plan.rectangular_bosses)
if ($returnedBosses.Count -ne 2 -or [string]$returnedBosses[0].corner_style -ne 'chamfer' -or
    [Math]::Abs(([double]$returnedBosses[0].corner_size_mm) - 5.0) -gt 0.001 -or
    [string]$returnedBosses[1].corner_style -ne 'round' -or
    [Math]::Abs(([double]$returnedBosses[1].corner_size_mm) - 7.0) -gt 0.001) {
    throw 'The returned Plan v5 does not contain the requested chamfer and round parameters.'
}
$envelope = @($result.data.plan.calculated.envelope_xyz_mm)
if ($envelope.Count -ne 3 -or [Math]::Abs(([double]$envelope[0]) - 200.0) -gt 0.001 -or
    [Math]::Abs(([double]$envelope[1]) - 120.0) -gt 0.001 -or
    [Math]::Abs(([double]$envelope[2]) - 28.0) -gt 0.001) {
    throw 'The calculated 200 x 120 x 28 mm envelope is incorrect.'
}
$materialOk = [bool]$result.data.material_assigned -and [bool]$result.data.material.verified -and
    ([string]$result.data.material.name -eq 'AISI 304')
if (-not $materialOk) { throw 'AISI 304 was not assigned and verified.' }
$written = @($result.data.written_properties.items)
if ($written.Count -lt 13) { throw 'Designation, name or audited Plan v5 properties were not all confirmed.' }
Write-Host ''
Write-Host 'PASS: Plan v5 chamfers, rounds, cuts, one-body topology, material and volume checks passed.' -ForegroundColor Green
Start-Process explorer.exe -ArgumentList "/select,`"$path`""
Read-Host 'Press Enter to close'
