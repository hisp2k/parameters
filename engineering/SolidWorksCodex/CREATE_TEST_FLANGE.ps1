$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'

$holes = @([ordered]@{ x_mm = 0; y_mm = 0; diameter_mm = 40 })
for ($i = 0; $i -lt 6; $i++) {
    $angle = 2.0 * [Math]::PI * $i / 6.0
    $holes += [ordered]@{
        x_mm = [Math]::Round(35.0 * [Math]::Cos($angle), 6)
        y_mm = [Math]::Round(35.0 * [Math]::Sin($angle), 6)
        diameter_mm = 8
    }
}

$partPlan = [ordered]@{
    plan_version = '1'
    outer_profile = [ordered]@{
        type = 'circle'
        diameter_mm = 100
    }
    thickness_mm = 10
    holes = $holes
}

$json = $partPlan | ConvertTo-Json -Depth 8 -Compress
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
Write-Host 'Creating a NEW flange from a generic model-generated plan:'
Write-Host 'outer D100 x 10 mm; centre hole D40; six D8 holes on PCD 70.'
Write-Host 'Existing documents will not be saved or edited.'
Write-Host ''
$raw = (& $exe --worker sw_create_part_from_plan $payload 2>&1 | Out-String).Trim()
Write-Host $raw
$result = $raw | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $result.ok) { throw 'SOLIDWORKS generic part creation failed.' }
$path = [string]$result.data.file_path
if (-not (Test-Path -LiteralPath $path)) { throw "The connector reported success but the file does not exist: $path" }
if ([string]$result.data.verification.status -ne 'PASS') { throw 'Generated volume was not verified.' }
$topology = $result.data.verification.topology
if ([string]$topology.status -ne 'PASS') { throw 'Generated analytic cylinders were not verified.' }
if (-not [bool]$topology.outer_circle.analytic_cylindrical_surface_confirmed) {
    throw 'The D100 outer profile is not an analytic cylindrical surface.'
}
Write-Host ''
Write-Host 'PASS: flange volume and analytic circular surfaces match the validated plan.' -ForegroundColor Green
Start-Process explorer.exe -ArgumentList "/select,`"$path`""
Read-Host 'Press Enter to close'
