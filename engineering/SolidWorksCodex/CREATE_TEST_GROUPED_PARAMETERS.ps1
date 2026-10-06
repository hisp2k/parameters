$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$workspace = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'SolidWorksCodex\Workspace'))

function Invoke-ConnectorWorker([string]$tool, [hashtable]$arguments) {
    $json = $arguments | ConvertTo-Json -Depth 16 -Compress
    $payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
    $raw = (& $exe --worker $tool $payload 2>&1 | Out-String).Trim()
    Write-Host $raw
    $workerExitCode = $LASTEXITCODE
    try { $result = $raw | ConvertFrom-Json }
    catch { throw "Connector worker returned invalid JSON for $tool. Raw output: $raw" }
    if ($workerExitCode -ne 0 -or -not $result.ok) {
        $code = [string]$result.error.code
        $message = [string]$result.error.message
        throw "Connector worker failed: $tool. ${code}: $message"
    }
    return $result.data
}

function Get-SharedFileSha256([string]$path) {
    $share = [IO.FileShare]([int][IO.FileShare]::ReadWrite -bor [int][IO.FileShare]::Delete)
    $stream = [IO.FileStream]::new(
        [IO.Path]::GetFullPath($path), [IO.FileMode]::Open,
        [IO.FileAccess]::Read, $share)
    try {
        $sha = [Security.Cryptography.SHA256]::Create()
        try { return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '') }
        finally { $sha.Dispose() }
    }
    finally { $stream.Dispose() }
}

function Get-OneEditableParameter($items, [string]$name, [double]$expectedMm) {
    $matches = @($items | Where-Object { [string]$_.name -eq $name })
    if ($matches.Count -ne 1 -or -not [bool]$matches[0].editable_by_connector -or
        [Math]::Abs([double]$matches[0].value_mm - $expectedMm) -gt 0.001) {
        throw "Expected one editable $name = $expectedMm mm; found $($matches.Count)."
    }
    return $matches[0]
}

Write-Host 'GROUPED 15-PARAMETER EDIT + DRAWING/PDF TEST' -ForegroundColor Cyan
Write-Host 'Creates a new test plate and changes length, width, thickness, four hole diameters'
Write-Host 'and eight hole offsets in ONE operation with ONE verified backup.'
Write-Host 'Existing documents are not edited or saved.'
Write-Host ''

$plate = Invoke-ConnectorWorker 'sw_create_plate' ([ordered]@{
    length_mm = 120
    width_mm = 80
    thickness_mm = 6
    hole_diameter_mm = 10
    edge_offset_x_mm = 15
    edge_offset_y_mm = 15
})
if ([string]$plate.connector_version -ne '2.2.2' -or
    [string]$plate.verification.status -ne 'PASS') {
    throw 'The installed connector is not version 2.2.2 or plate creation failed.'
}

$opened = Invoke-ConnectorWorker 'sw_open_local_file' ([ordered]@{ file_path = [string]$plate.file_path })
if ([string]$opened.connector_version -ne '2.2.2') { throw 'The exact test plate was not reopened.' }

$parameters = Invoke-ConnectorWorker 'sw_parameters' ([ordered]@{})
$items = @($parameters.data.items)
$requested = @(
    [pscustomobject]@{ Name = 'AI_Length'; Old = 120.0; New = 140.0 },
    [pscustomobject]@{ Name = 'AI_Width'; Old = 80.0; New = 90.0 },
    [pscustomobject]@{ Name = 'AI_Thickness'; Old = 6.0; New = 8.0 }
)
for ($i = 1; $i -le 4; $i++) {
    $requested += [pscustomobject]@{ Name = "AI_Hole_Diameter_$i"; Old = 10.0; New = 12.0 }
    $requested += [pscustomobject]@{ Name = "AI_Hole_Offset_X_$i"; Old = 15.0; New = 18.0 }
    $requested += [pscustomobject]@{ Name = "AI_Hole_Offset_Y_$i"; Old = 15.0; New = 16.0 }
}

$changes = @()
foreach ($request in $requested) {
    $parameter = Get-OneEditableParameter $items $request.Name $request.Old
    $changes += [ordered]@{
        full_name = [string]$parameter.full_name
        expected_current_mm = [double]$request.Old
        new_value_mm = [double]$request.New
    }
}
if ($changes.Count -ne 15) { throw "Expected exactly 15 grouped changes; found $($changes.Count)." }

$sourcePath = [IO.Path]::GetFullPath([string]$plate.file_path)
$sourceHashBefore = Get-SharedFileSha256 $sourcePath
Write-Host ''
Write-Host 'Applying all 15 changes...'
$changed = Invoke-ConnectorWorker 'sw_set_parameters' ([ordered]@{ changes = $changes })
if ([string]$changed.connector_version -ne '2.2.2' -or
    [string]$changed.verification.status -ne 'PASS' -or
    -not [bool]$changed.verification.all_requested_values_confirmed -or
    [int]$changed.change_count -ne 15) {
    throw 'The grouped parameter change did not pass every connector verification.'
}
if (-not (Test-Path -LiteralPath ([string]$changed.backup_path) -PathType Leaf)) {
    throw 'The automatic backup was not created.'
}
if ((Get-SharedFileSha256 ([string]$changed.backup_path)) -ne $sourceHashBefore) {
    throw 'The automatic backup is not byte-identical to the original test plate.'
}
if ((Get-SharedFileSha256 $sourcePath) -eq $sourceHashBefore) {
    throw 'The edited SLDPRT bytes did not change.'
}

$afterParameters = Invoke-ConnectorWorker 'sw_parameters' ([ordered]@{})
$afterItems = @($afterParameters.data.items)
foreach ($request in $requested) {
    [void](Get-OneEditableParameter $afterItems $request.Name $request.New)
}

$part = Invoke-ConnectorWorker 'sw_part' ([ordered]@{})
$sizes = @($part.data.bounding_box.size_xyz.value)
if ($sizes.Count -ne 3 -or
    [Math]::Abs([double]$sizes[0] - 140.0) -gt 0.05 -or
    [Math]::Abs([double]$sizes[1] - 90.0) -gt 0.05 -or
    [Math]::Abs([double]$sizes[2] - 8.0) -gt 0.05) {
    throw 'The rebuilt bounding box is not approximately 140 x 90 x 8 mm.'
}
$expectedVolumeM3 = ((140.0 * 90.0) - (4.0 * [Math]::PI * 6.0 * 6.0)) * 8.0 / 1000000000.0
$actualVolumeM3 = [double]$part.data.mass_properties.volume.value
$relativeVolumeError = [Math]::Abs($actualVolumeM3 - $expectedVolumeM3) / $expectedVolumeM3
if ($relativeVolumeError -gt 0.001) {
    throw "Final CAD volume differs from the requested geometry. relative_error=$relativeVolumeError"
}

Write-Host ''
Write-Host 'Creating a drawing and PDF from the edited part...'
$drawing = Invoke-ConnectorWorker 'sw_create_drawing' ([ordered]@{ projection = 'first_angle'; dimensions = 'model' })
if ([string]$drawing.connector_version -ne '2.2.2' -or
    [string]$drawing.verification.status -ne 'PASS' -or
    [int]$drawing.verification.referenced_model_view_count -lt 1 -or
    [int]$drawing.verification.display_dimension_count -lt 15) {
    throw 'Drawing creation or imported model-dimension verification failed.'
}
$audit = Invoke-ConnectorWorker 'sw_drawing' ([ordered]@{})
if ([string]$audit.data.verification.status -ne 'PASS' -or
    [int]$audit.data.referenced_model_view_count -lt 1 -or
    [int]$audit.data.display_dimension_count -lt 15) {
    throw 'Drawing audit failed.'
}
$pdf = Invoke-ConnectorWorker 'sw_export_workspace_pdf' ([ordered]@{})
if ([string]$pdf.connector_version -ne '2.2.2' -or
    [string]$pdf.verification.status -ne 'PASS' -or
    -not [bool]$pdf.source_drawing_unchanged -or
    -not (Test-Path -LiteralPath ([string]$pdf.file_path) -PathType Leaf)) {
    throw 'PDF export verification failed.'
}

Write-Host ''
Write-Host 'PASS: 15 grouped parameters, one backup, rebuild, exact volume, drawing and PDF passed.' -ForegroundColor Green
Write-Host "Edited part: $sourcePath"
Write-Host "Backup: $($changed.backup_path)"
Write-Host 'Verified dimensions: 140 x 90 x 8 mm; four D12 holes; X offsets 18 mm; Y offsets 16 mm.'
Write-Host "Drawing: $($drawing.file_path)"
Write-Host "PDF: $($pdf.file_path)"
Write-Host 'Human review is still required before manufacturing.' -ForegroundColor Yellow
Start-Process explorer.exe -ArgumentList "`"$workspace`""
Read-Host 'Press Enter to close'
