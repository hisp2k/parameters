$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$plateArgs = [ordered]@{
    length_mm = 100
    width_mm = 60
    thickness_mm = 5
    hole_diameter_mm = 8
    edge_offset_x_mm = 10
    edge_offset_y_mm = 10
}
$json = $plateArgs | ConvertTo-Json -Compress
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
Write-Host 'Creating a NEW test plate: 100 x 60 x 5 mm, four holes D8, offsets 10 x 10 mm.'
Write-Host 'Existing documents will not be saved or edited.'
Write-Host ''
$raw = (& $exe --worker sw_create_plate $payload 2>&1 | Out-String).Trim()
Write-Host $raw
$result = $raw | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $result.ok) { throw 'SolidWorks plate creation failed.' }
if ([string]$result.data.connector_version -ne '2.2.2') { throw 'The installed connector is not version 2.2.2.' }
if ([string]$result.data.driving_dimensions.status -ne 'PASS' -or
    [int]$result.data.driving_dimensions.total_marked_for_drawing -lt 15) {
    throw 'The plate does not contain all fifteen marked driving dimensions.'
}
$path = [string]$result.data.file_path
if (-not (Test-Path -LiteralPath $path)) { throw "The connector reported success but the file does not exist: $path" }
Write-Host ''
Write-Host 'PASS: SLDPRT volume and fifteen marked driving dimensions passed.' -ForegroundColor Green
Start-Process explorer.exe -ArgumentList "/select,`"$path`""
Read-Host 'Press Enter to close'
