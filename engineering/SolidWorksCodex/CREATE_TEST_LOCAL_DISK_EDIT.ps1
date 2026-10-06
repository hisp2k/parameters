$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$workspace = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'SolidWorksCodex\Workspace'))
$localTest = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'SolidWorksCodex\LocalDiskTest'))

function Invoke-ConnectorWorker([string]$tool, [hashtable]$arguments) {
    $json = $arguments | ConvertTo-Json -Depth 12 -Compress
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

function Assert-LocalTestFile([string]$path, [string]$extension) {
    $full = [IO.Path]::GetFullPath($path)
    $prefix = $localTest.TrimEnd('\') + '\'
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "File is outside the local fixed-disk test folder: $full"
    }
    if ([IO.Path]::GetExtension($full) -ine $extension -or -not (Test-Path -LiteralPath $full -PathType Leaf)) {
        throw "Expected saved $extension file: $full"
    }
}

function Get-SharedFileSha256([string]$path) {
    $share = [IO.FileShare]([int][IO.FileShare]::ReadWrite -bor [int][IO.FileShare]::Delete)
    $stream = [IO.FileStream]::new(
        [IO.Path]::GetFullPath($path),
        [IO.FileMode]::Open,
        [IO.FileAccess]::Read,
        $share
    )
    try {
        $sha = [Security.Cryptography.SHA256]::Create()
        try { return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '') }
        finally { $sha.Dispose() }
    }
    finally { $stream.Dispose() }
}

Write-Host 'LOCAL FIXED-DISK EDIT TEST' -ForegroundColor Cyan
Write-Host 'This test copies a generated part OUTSIDE Workspace, opens it by full local path,'
Write-Host 'changes only the local copy, creates verified backups, a drawing and a PDF beside it.'
Write-Host 'UNC paths, mapped network drives and removable drives remain blocked.'
Write-Host ''

New-Item -ItemType Directory -Path $localTest -Force | Out-Null

$plate = Invoke-ConnectorWorker 'sw_create_plate' ([ordered]@{
    length_mm = 120
    width_mm = 80
    thickness_mm = 6
    hole_diameter_mm = 10
    edge_offset_x_mm = 15
    edge_offset_y_mm = 15
})
if ([string]$plate.connector_version -ne '2.2.2' -or [string]$plate.verification.status -ne 'PASS') {
    throw 'The installed connector is not version 2.2.2 or plate verification failed.'
}

$stamp = (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + ([guid]::NewGuid().ToString('N')).Substring(0, 8)
$localPart = Join-Path $localTest ("LOCAL_DISK_PLATE_${stamp}.SLDPRT")
Copy-Item -LiteralPath ([string]$plate.file_path) -Destination $localPart
Assert-LocalTestFile $localPart '.SLDPRT'
$originalHash = Get-SharedFileSha256 $localPart

Write-Host ''
Write-Host 'Opening the copied part through the fixed-local-disk gate...'
$opened = Invoke-ConnectorWorker 'sw_open_local_file' ([ordered]@{ file_path = $localPart })
if ([string]$opened.connector_version -ne '2.2.2' -or [string]$opened.document_type -ne 'PART' -or
    [bool]$opened.inside_workspace) {
    throw 'The copied local part was not opened outside Workspace.'
}

$document = Invoke-ConnectorWorker 'sw_document' ([ordered]@{})
if ([string]$document.context.storage_scope -ne 'LOCAL_FIXED_DISK' -or
    -not [bool]$document.context.connector_write_allowed) {
    throw 'sw_document did not authorize the verified local fixed-disk part.'
}

$parameters = Invoke-ConnectorWorker 'sw_parameters' ([ordered]@{})
$length = @($parameters.data.items | Where-Object { [string]$_.name -eq 'AI_Length' })
$width = @($parameters.data.items | Where-Object { [string]$_.name -eq 'AI_Width' })
$thickness = @($parameters.data.items | Where-Object { [string]$_.name -eq 'AI_Thickness' })
if ($length.Count -ne 1 -or $width.Count -ne 1 -or $thickness.Count -ne 1 -or
    -not [bool]$length[0].editable_by_connector -or -not [bool]$width[0].editable_by_connector -or
    -not [bool]$thickness[0].editable_by_connector) {
    throw 'The local AI_Length, AI_Width and AI_Thickness parameters were not found or editable.'
}

Write-Host ''
Write-Host 'Changing the existing LOCAL copy from 120 x 80 x 6 to 135 x 85 x 7 mm...'
$changed = Invoke-ConnectorWorker 'sw_set_parameters' ([ordered]@{
    changes = @(
        [ordered]@{ full_name = [string]$length[0].full_name; expected_current_mm = 120; new_value_mm = 135 },
        [ordered]@{ full_name = [string]$width[0].full_name; expected_current_mm = 80; new_value_mm = 85 },
        [ordered]@{ full_name = [string]$thickness[0].full_name; expected_current_mm = 6; new_value_mm = 7 }
    )
})
if ([string]$changed.connector_version -ne '2.2.2' -or [string]$changed.verification.status -ne 'PASS' -or
    [int]$changed.change_count -ne 3 -or [bool]$changed.inside_workspace) {
    throw 'The local grouped parameter change did not pass.'
}
Assert-LocalTestFile ([string]$changed.backup_path) '.SLDPRT'
if ((Get-SharedFileSha256 ([string]$changed.backup_path)) -ne $originalHash) {
    throw 'The automatic parameter backup does not match the original local file.'
}
if ((Get-SharedFileSha256 $localPart) -eq $originalHash) {
    throw 'The requested local part did not change on disk.'
}

$part = Invoke-ConnectorWorker 'sw_part' ([ordered]@{})
if ([Math]::Abs([double]$part.data.bounding_box.size_xyz.value[0] - 135.0) -gt 0.05 -or
    [Math]::Abs([double]$part.data.bounding_box.size_xyz.value[1] - 85.0) -gt 0.05 -or
    [Math]::Abs([double]$part.data.bounding_box.size_xyz.value[2] - 7.0) -gt 0.05) {
    throw 'The changed local part bounding box is not approximately 135 x 85 x 7 mm.'
}

Write-Host ''
Write-Host 'Writing tested properties and AISI 304 to the local part...'
$properties = Invoke-ConnectorWorker 'sw_set_workspace_properties' ([ordered]@{
    designation = 'LOCAL.TEST.001'
    name = 'Local fixed-disk test plate'
    material = 'AISI 304'
})
if ([string]$properties.connector_version -ne '2.2.2' -or -not [bool]$properties.material.verified -or
    [bool]$properties.inside_workspace) {
    throw 'The local property/material update did not pass.'
}
Assert-LocalTestFile ([string]$properties.backup_path) '.SLDPRT'

Write-Host ''
Write-Host 'Creating a drawing and PDF beside the local part...'
$drawing = Invoke-ConnectorWorker 'sw_create_drawing' ([ordered]@{ projection = 'first_angle'; dimensions = 'model' })
if ([string]$drawing.connector_version -ne '2.2.2' -or [string]$drawing.verification.status -ne 'PASS' -or
    [int]$drawing.verification.referenced_model_view_count -lt 1 -or
    [int]$drawing.verification.display_dimension_count -lt 15 -or [bool]$drawing.inside_workspace -or
    [string]$drawing.source_sha256_before -ne [string]$drawing.source_sha256_after) {
    throw 'The local drawing verification did not pass.'
}
Assert-LocalTestFile ([string]$drawing.file_path) '.SLDDRW'

$audit = Invoke-ConnectorWorker 'sw_drawing' ([ordered]@{})
if ([string]$audit.data.verification.status -ne 'PASS' -or [int]$audit.data.referenced_model_view_count -lt 1) {
    throw 'The local drawing audit did not pass.'
}

$pdf = Invoke-ConnectorWorker 'sw_export_workspace_pdf' ([ordered]@{})
if ([string]$pdf.connector_version -ne '2.2.2' -or [string]$pdf.verification.status -ne 'PASS' -or
    [bool]$pdf.inside_workspace -or [string]$pdf.source_sha256_before -ne [string]$pdf.source_sha256_after) {
    throw 'The local PDF export verification did not pass.'
}
Assert-LocalTestFile ([string]$pdf.file_path) '.PDF'

Write-Host ''
Write-Host 'PASS: local fixed-disk open, backup, edit, properties, drawing and PDF passed; network paths remain blocked.' -ForegroundColor Green
Write-Host "Changed local part: $localPart"
Write-Host "Parameter backup: $($changed.backup_path)"
Write-Host "Property backup: $($properties.backup_path)"
Write-Host "Drawing: $($drawing.file_path)"
Write-Host "PDF: $($pdf.file_path)"
Write-Host 'Every output above is outside Workspace but on the same verified local fixed disk.' -ForegroundColor Yellow
Start-Process explorer.exe -ArgumentList "`"$localTest`""
Read-Host 'Press Enter to close'
