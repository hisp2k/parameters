$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'

$outer = @(
    [ordered]@{ x_mm = 0;   diameter_mm = 48 },
    [ordered]@{ x_mm = 1;   diameter_mm = 50 },
    [ordered]@{ x_mm = 9;   diameter_mm = 50 },
    [ordered]@{ x_mm = 10;  diameter_mm = 48 },
    [ordered]@{ x_mm = 10;  diameter_mm = 35 },
    [ordered]@{ x_mm = 35;  diameter_mm = 35 },
    [ordered]@{ x_mm = 36;  diameter_mm = 33 },
    [ordered]@{ x_mm = 66;  diameter_mm = 33 },
    [ordered]@{ x_mm = 67;  diameter_mm = 35 },
    [ordered]@{ x_mm = 99;  diameter_mm = 35 },
    [ordered]@{ x_mm = 100; diameter_mm = 33 }
)
$bore = @(
    [ordered]@{ x_mm = 46;        diameter_mm = 0 },
    [ordered]@{ x_mm = 47.15;     diameter_mm = 4 },
    [ordered]@{ x_mm = 86.201721; diameter_mm = 4 },
    [ordered]@{ x_mm = 87.553658; diameter_mm = 8.5 },
    [ordered]@{ x_mm = 100;       diameter_mm = 8.5 }
)
$partPlan = [ordered]@{
    plan_version = '2'
    outer_profile = $outer
    axial_bore_profile = $bore
    radial_holes = @([ordered]@{ x_mm = 51; diameter_mm = 4 })
    side_flat_slots = @([ordered]@{
        x_start_mm = 92
        x_end_mm = 95.2
        floor_radius_mm = 14.5
        side = 'positive'
    })
    reference_volume_mm3 = 100957.212334685
}

$json = $partPlan | ConvertTo-Json -Depth 8 -Compress
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
Write-Host 'Creating a NEW turned chain-pin test part from Plan v2:'
Write-Host '100 mm long; D50 flange; D35/D33 steps; blind stepped axial bore; radial D4; side flat slot.'
Write-Host 'Reference STEP volume: 100957.212334685 mm3. Existing documents will not be saved or edited.'
Write-Host ''
$raw = (& $exe --worker sw_create_turned_part_from_plan $payload 2>&1 | Out-String).Trim()
Write-Host $raw
$result = $raw | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $result.ok) { throw 'SOLIDWORKS turned-part creation failed.' }
$path = [string]$result.data.file_path
if (-not (Test-Path -LiteralPath $path)) { throw "The connector reported success but the file does not exist: $path" }
if ([string]$result.data.verification.status -ne 'PASS') { throw 'Generated turned-part geometry was not verified.' }
$referenceError = [double]$result.data.verification.reference_relative_error
if ($referenceError -gt 0.0005) { throw "Reference-volume error is too high: $referenceError" }
Write-Host ''
Write-Host 'PASS: turned chain-pin SLDPRT exists; axial profile and final reference volume passed.' -ForegroundColor Green
Start-Process explorer.exe -ArgumentList "/select,`"$path`""
Read-Host 'Press Enter to close'
