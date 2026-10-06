$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$partName = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('0JrQvtC90YLRgNC+0LvRjNC90LDRjyDQv9C70LjRgtCwINGBINC60LDRgNC80LDQvdCw0LzQuA=='))

$partPlan = [ordered]@{
    plan_version = '3'
    outer_profile = [ordered]@{
        type = 'rectangle'
        width_mm = 160
        height_mm = 100
    }
    thickness_mm = 12
    rectangular_pockets = @(
        [ordered]@{ x_mm = -45; y_mm = 22; width_mm = 36; height_mm = 22; depth_mm = 4 }
    )
    circular_pockets = @(
        [ordered]@{ x_mm = 45; y_mm = 22; diameter_mm = 24; depth_mm = 6 }
    )
    straight_slots = @(
        [ordered]@{ x1_mm = -25; y1_mm = -25; x2_mm = 25; y2_mm = -25; width_mm = 12; cut_type = 'through' }
    )
    properties = [ordered]@{
        designation = 'AI.TEST.070'
        name = $partName
    }
    material = 'AISI 304'
}

$json = $partPlan | ConvertTo-Json -Depth 10 -Compress
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
Write-Host 'Creating a NEW Plan v3 control plate: 160 x 100 x 12 mm.'
Write-Host 'Cuts: rectangular blind pocket 36 x 22 x 4; circular blind pocket D24 x 6; through slot 50 x 12.'
Write-Host 'Material AISI 304 and audited creation properties will be assigned and read back.'
Write-Host 'Existing documents will not be saved or edited.'
Write-Host ''
$raw = (& $exe --worker sw_create_part_from_plan $payload 2>&1 | Out-String).Trim()
Write-Host $raw
$result = $raw | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $result.ok) { throw 'SOLIDWORKS Plan v3 control-part creation failed.' }
$path = [string]$result.data.file_path
if (-not (Test-Path -LiteralPath $path)) { throw "The connector reported success but the file does not exist: $path" }
if ([string]$result.data.connector_version -ne '2.2.2') { throw 'The installed connector is not version 2.2.2.' }
if ([string]$result.data.verification.status -ne 'PASS') { throw 'Final CAD volume was not verified.' }
if ([string]$result.data.verification.base.status -ne 'PASS' -or
    [string]$result.data.verification.base.topology.status -ne 'PASS') {
    throw 'The base body was not verified before cuts.'
}
$cuts = @($result.data.verification.cuts)
if ($cuts.Count -ne 3 -or @($cuts | Where-Object { [string]$_.status -ne 'PASS' }).Count -ne 0) {
    throw 'Every one of the three cuts must pass its removed-volume check.'
}
$topology = $result.data.verification.topology
if ([string]$topology.status -ne 'PASS') { throw 'Final analytic cylindrical cut surfaces were not verified.' }
$diameters = @($topology.actual_diameters_mm)
$slotCaps = @($diameters | Where-Object { [Math]::Abs(([double]$_) - 12.0) -le 0.001 }).Count
$roundPocket = @($diameters | Where-Object { [Math]::Abs(([double]$_) - 24.0) -le 0.001 }).Count
if ($diameters.Count -ne 3 -or $slotCaps -ne 2 -or $roundPocket -ne 1) {
    throw 'Expected two analytic D12 slot end surfaces and one analytic D24 pocket surface.'
}
if (@($result.data.plan.rectangular_pockets).Count -ne 1 -or
    @($result.data.plan.circular_pockets).Count -ne 1 -or
    @($result.data.plan.straight_slots).Count -ne 1) {
    throw 'The returned Plan v3 does not contain all requested cuts.'
}
$materialOk = [bool]$result.data.material_assigned -and [bool]$result.data.material.verified -and
    ([string]$result.data.material.name -eq 'AISI 304')
if (-not $materialOk) { throw 'AISI 304 was not assigned and verified.' }
$written = @($result.data.written_properties.items)
if ($written.Count -lt 9) { throw 'Designation, name or audited creation properties were not all confirmed.' }
Write-Host ''
Write-Host 'PASS: Plan v3 rectangular pocket, circular pocket, through slot, material, properties and geometry checks passed.' -ForegroundColor Green
Start-Process explorer.exe -ArgumentList "/select,`"$path`""
Read-Host 'Press Enter to close'
