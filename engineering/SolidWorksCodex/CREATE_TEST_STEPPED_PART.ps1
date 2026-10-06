$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$partName = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('0KHRgtGD0L/QtdC90YfQsNGC0LDRjyDQutC+0L3RgtGA0L7Qu9GM0L3QsNGPINC/0LvQuNGC0LA='))

$partPlan = [ordered]@{
    plan_version = '4'
    outer_profile = [ordered]@{
        type = 'rectangle'
        width_mm = 180
        height_mm = 110
    }
    thickness_mm = 12
    rectangular_pockets = @(
        [ordered]@{ x_mm = 64; y_mm = -25; width_mm = 24; height_mm = 16; depth_mm = 4 }
    )
    circular_pockets = @(
        [ordered]@{ x_mm = 0; y_mm = 25; diameter_mm = 20; depth_mm = 5 }
    )
    straight_slots = @(
        [ordered]@{ x1_mm = -35; y1_mm = -28; x2_mm = 35; y2_mm = -28; width_mm = 12; cut_type = 'through' }
    )
    rectangular_bosses = @(
        [ordered]@{ x_mm = 45; y_mm = 25; width_mm = 46; height_mm = 24; extrusion_mm = 10 }
    )
    circular_bosses = @(
        [ordered]@{ x_mm = -50; y_mm = 25; diameter_mm = 36; extrusion_mm = 18 }
    )
    properties = [ordered]@{
        designation = 'AI.TEST.080'
        name = $partName
    }
    material = 'AISI 304'
}

$json = $partPlan | ConvertTo-Json -Depth 10 -Compress
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
Write-Host 'Creating a NEW Plan v4 stepped control part: 180 x 110 x 12 mm base.'
Write-Host 'Bosses: rectangular 46 x 24 x 10 and circular D36 x 18.'
Write-Host 'Cuts: rectangular blind pocket, circular blind pocket and a through slot.'
Write-Host 'Material AISI 304 and audited creation properties will be assigned and read back.'
Write-Host 'Existing documents will not be saved or edited.'
Write-Host ''
$raw = (& $exe --worker sw_create_part_from_plan $payload 2>&1 | Out-String).Trim()
Write-Host $raw
$result = $raw | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $result.ok) { throw 'SOLIDWORKS Plan v4 stepped-part creation failed.' }
$path = [string]$result.data.file_path
if (-not (Test-Path -LiteralPath $path)) { throw "The connector reported success but the file does not exist: $path" }
if ([string]$result.data.connector_version -ne '2.2.2') { throw 'The installed connector is not version 2.2.2.' }
if ([string]$result.data.verification.status -ne 'PASS') { throw 'Final CAD volume was not verified.' }
if ([string]$result.data.verification.base.status -ne 'PASS' -or
    [string]$result.data.verification.base.topology.status -ne 'PASS') {
    throw 'The base body was not verified before bosses and cuts.'
}
if ([string]$result.data.verification.after_bosses.status -ne 'PASS') {
    throw 'The total body volume after bosses was not verified.'
}
$bosses = @($result.data.verification.bosses)
if ($bosses.Count -ne 2 -or @($bosses | Where-Object { [string]$_.status -ne 'PASS' }).Count -ne 0) {
    throw 'Both bosses must pass their added-volume checks.'
}
$cuts = @($result.data.verification.cuts)
if ($cuts.Count -ne 3 -or @($cuts | Where-Object { [string]$_.status -ne 'PASS' }).Count -ne 0) {
    throw 'Every one of the three cuts must pass its removed-volume check.'
}
$topology = $result.data.verification.topology
if ([string]$topology.status -ne 'PASS' -or [int]$topology.solid_body_count -ne 1) {
    throw 'The final result is not one verified solid body.'
}
$diameters = @($topology.actual_diameters_mm)
$slotCaps = @($diameters | Where-Object { [Math]::Abs(([double]$_) - 12.0) -le 0.001 }).Count
$roundPocket = @($diameters | Where-Object { [Math]::Abs(([double]$_) - 20.0) -le 0.001 }).Count
$roundBoss = @($diameters | Where-Object { [Math]::Abs(([double]$_) - 36.0) -le 0.001 }).Count
if ($diameters.Count -ne 4 -or $slotCaps -ne 2 -or $roundPocket -ne 1 -or $roundBoss -ne 1) {
    throw 'Expected D36 boss, D20 pocket and two D12 slot-end cylindrical surfaces.'
}
if (@($result.data.plan.rectangular_bosses).Count -ne 1 -or
    @($result.data.plan.circular_bosses).Count -ne 1 -or
    @($result.data.plan.rectangular_pockets).Count -ne 1 -or
    @($result.data.plan.circular_pockets).Count -ne 1 -or
    @($result.data.plan.straight_slots).Count -ne 1) {
    throw 'The returned Plan v4 does not contain all requested bosses and cuts.'
}
$envelope = @($result.data.plan.calculated.envelope_xyz_mm)
if ($envelope.Count -ne 3 -or [Math]::Abs(([double]$envelope[0]) - 180.0) -gt 0.001 -or
    [Math]::Abs(([double]$envelope[1]) - 110.0) -gt 0.001 -or
    [Math]::Abs(([double]$envelope[2]) - 30.0) -gt 0.001) {
    throw 'The calculated 180 x 110 x 30 mm envelope is incorrect.'
}
$materialOk = [bool]$result.data.material_assigned -and [bool]$result.data.material.verified -and
    ([string]$result.data.material.name -eq 'AISI 304')
if (-not $materialOk) { throw 'AISI 304 was not assigned and verified.' }
$written = @($result.data.written_properties.items)
if ($written.Count -lt 11) { throw 'Designation, name or audited creation properties were not all confirmed.' }
Write-Host ''
Write-Host 'PASS: Plan v4 bosses, cuts, one-body topology, material, properties and volume checks passed.' -ForegroundColor Green
Start-Process explorer.exe -ArgumentList "/select,`"$path`""
Read-Host 'Press Enter to close'
