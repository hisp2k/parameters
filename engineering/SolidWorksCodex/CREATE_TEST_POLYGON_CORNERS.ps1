$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$plan = [ordered]@{
    plan_version = '6'
    outer_profile = [ordered]@{
        type = 'polygon'
        points_mm = @(
            [ordered]@{ x_mm=-100; y_mm=-60; corner_style='round'; corner_size_mm=10 },
            [ordered]@{ x_mm=100; y_mm=-60; corner_style='chamfer'; corner_size_mm=8 },
            [ordered]@{ x_mm=100; y_mm=60 },
            [ordered]@{ x_mm=-100; y_mm=60 }
        )
    }
    thickness_mm = 5
    holes = @([ordered]@{ x_mm=0; y_mm=0; diameter_mm=12 })
    properties = [ordered]@{ designation='AI.PLAN6.001'; name='Plan v6 polygon corners' }
    material = 'AISI 304'
}
$json = $plan | ConvertTo-Json -Depth 12 -Compress
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
Write-Host 'PLAN V6 TEST: polygon with one true R10 corner, one 8 mm chamfer and one D12 hole.'
Write-Host 'Existing documents will not be saved or edited.'
$raw = (& $exe --worker sw_create_part_from_plan $payload 2>&1 | Out-String).Trim()
Write-Host $raw
$result = $raw | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $result.ok) { throw 'SOLIDWORKS Plan v6 polygon creation failed.' }
$data = $result.data
if ([string]$data.connector_version -ne '2.2.2') { throw 'The installed connector is not version 2.2.2.' }
if (-not (Test-Path -LiteralPath ([string]$data.file_path))) { throw 'Generated SLDPRT was not saved.' }
if ([string]$data.verification.status -ne 'PASS' -or
    [string]$data.verification.base.topology.status -ne 'PASS' -or
    [string]$data.verification.topology.status -ne 'PASS') {
    throw 'Volume or B-rep topology verification did not pass.'
}
if ([int]$data.verification.topology.rounded_outer_profile_corners.expected_count -ne 1 -or
    [int]$data.verification.topology.through_holes.expected_count -ne 1) {
    throw 'Expected one rounded outer corner and one through hole.'
}
Write-Host ''
Write-Host 'PASS: Plan v6 polygon round, chamfer, hole, volume and final topology passed.' -ForegroundColor Green
Start-Process explorer.exe -ArgumentList "/select,`"$($data.file_path)`""
Read-Host 'Press Enter to close'
