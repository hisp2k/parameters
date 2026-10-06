$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$workspace = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'SolidWorksCodex\Workspace'))

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

function Assert-WorkspaceFile([string]$path, [string]$extension) {
    $full = [IO.Path]::GetFullPath($path)
    $prefix = $workspace.TrimEnd('\') + '\'
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "File is outside the protected workspace: $full"
    }
    if ([IO.Path]::GetExtension($full) -ine $extension -or -not (Test-Path -LiteralPath $full -PathType Leaf)) {
        throw "Expected saved $extension file: $full"
    }
}

Write-Host 'FINAL LOCAL WORKSPACE TEST' -ForegroundColor Cyan
Write-Host 'This creates one new test plate and one drawing draft in the protected local Workspace.'
Write-Host 'Existing documents are not saved, edited or closed.'
Write-Host ''

$plate = Invoke-ConnectorWorker 'sw_create_plate' ([ordered]@{
    length_mm = 120
    width_mm = 80
    thickness_mm = 6
    hole_diameter_mm = 10
    edge_offset_x_mm = 15
    edge_offset_y_mm = 15
})
if ([string]$plate.connector_version -ne '2.2.2') { throw 'The installed connector is not version 2.2.2.' }
if ([string]$plate.verification.status -ne 'PASS') { throw 'Plate geometry verification did not pass.' }
if ([string]$plate.driving_dimensions.status -ne 'PASS' -or
    [int]$plate.driving_dimensions.total_marked_for_drawing -lt 15) {
    throw 'Plate driving-dimension verification did not pass.'
}
Assert-WorkspaceFile ([string]$plate.file_path) '.SLDPRT'

Write-Host ''
Write-Host 'Explicitly activating the new Workspace part...'
$opened = Invoke-ConnectorWorker 'sw_open_workspace_file' ([ordered]@{
    file_name = [IO.Path]::GetFileName([string]$plate.file_path)
})
if ([string]$opened.document_type -ne 'PART') { throw 'The created Workspace part was not activated.' }

Write-Host ''
Write-Host 'Reading connector-managed driving parameters...'
$parameters = Invoke-ConnectorWorker 'sw_parameters' ([ordered]@{})
$lengthMatches = @($parameters.data.items | Where-Object { [string]$_.name -eq 'AI_Length' })
$widthMatches = @($parameters.data.items | Where-Object { [string]$_.name -eq 'AI_Width' })
$thicknessMatches = @($parameters.data.items | Where-Object { [string]$_.name -eq 'AI_Thickness' })
if ($lengthMatches.Count -ne 1 -or $widthMatches.Count -ne 1 -or $thicknessMatches.Count -ne 1 -or
    -not [bool]$lengthMatches[0].editable_by_connector -or
    -not [bool]$widthMatches[0].editable_by_connector -or
    -not [bool]$thicknessMatches[0].editable_by_connector) {
    throw 'The AI_Length, AI_Width and AI_Thickness parameters were not found or editable.'
}

Write-Host ''
Write-Host 'Creating a NEW 140 x 90 x 8 mm parameter variant; the 120 x 80 x 6 source remains unchanged...'
$parameterChange = Invoke-ConnectorWorker 'sw_create_parameter_variant' ([ordered]@{
    source_file_name = [IO.Path]::GetFileName([string]$plate.file_path)
    changes = @(
        [ordered]@{ full_name = [string]$lengthMatches[0].full_name; expected_current_mm = 120; new_value_mm = 140 },
        [ordered]@{ full_name = [string]$widthMatches[0].full_name; expected_current_mm = 80; new_value_mm = 90 },
        [ordered]@{ full_name = [string]$thicknessMatches[0].full_name; expected_current_mm = 6; new_value_mm = 8 }
    )
})
if ([string]$parameterChange.connector_version -ne '2.2.2' -or
    [string]$parameterChange.verification.status -ne 'PASS' -or
    [int]$parameterChange.change_count -ne 3 -or
    -not [bool]$parameterChange.source_unchanged -or
    [string]$parameterChange.source_sha256_before -ne [string]$parameterChange.source_sha256_after) {
    throw 'Parameter-variant creation verification did not pass.'
}
Assert-WorkspaceFile ([string]$parameterChange.variant_path) '.SLDPRT'
Assert-WorkspaceFile ([string]$parameterChange.source_path) '.SLDPRT'

$parametersAfter = Invoke-ConnectorWorker 'sw_parameters' ([ordered]@{})
$lengthAfter = @($parametersAfter.data.items | Where-Object { [string]$_.name -eq 'AI_Length' })
$widthAfter = @($parametersAfter.data.items | Where-Object { [string]$_.name -eq 'AI_Width' })
$thicknessAfter = @($parametersAfter.data.items | Where-Object { [string]$_.name -eq 'AI_Thickness' })
if ([Math]::Abs([double]$lengthAfter[0].value_mm - 140.0) -gt 0.001 -or
    [Math]::Abs([double]$widthAfter[0].value_mm - 90.0) -gt 0.001 -or
    [Math]::Abs([double]$thicknessAfter[0].value_mm - 8.0) -gt 0.001) {
    throw 'Grouped AI_* values did not remain after save.'
}
$partAfter = Invoke-ConnectorWorker 'sw_part' ([ordered]@{})
if ([Math]::Abs([double]$partAfter.data.bounding_box.size_xyz.value[0] - 140.0) -gt 0.05 -or
    [Math]::Abs([double]$partAfter.data.bounding_box.size_xyz.value[1] - 90.0) -gt 0.05 -or
    [Math]::Abs([double]$partAfter.data.bounding_box.size_xyz.value[2] - 8.0) -gt 0.05) {
    throw 'The rebuilt part bounding box is not approximately 140 x 90 x 8 mm.'
}

Write-Host ''
Write-Host 'Creating a first-angle drawing and importing existing model dimensions...'
$drawing = Invoke-ConnectorWorker 'sw_create_drawing' ([ordered]@{ projection = 'first_angle'; dimensions = 'model' })
if ([string]$drawing.connector_version -ne '2.2.2') { throw 'The installed connector is not version 2.2.2.' }
if ([string]$drawing.verification.status -ne 'PASS' -or
    [int]$drawing.verification.referenced_model_view_count -lt 1 -or
    [int]$drawing.verification.display_dimension_count -lt 15) {
    throw 'Drawing view or imported-dimension verification did not pass.'
}
Assert-WorkspaceFile ([string]$drawing.file_path) '.SLDDRW'

Write-Host ''
Write-Host 'Auditing the active drawing through the connector...'
$audit = Invoke-ConnectorWorker 'sw_drawing' ([ordered]@{})
if ([string]$audit.context.document_type -ne 'DRAWING' -or
    [string]$audit.data.verification.status -ne 'PASS' -or
    [int]$audit.data.referenced_model_view_count -lt 1 -or
    [int]$audit.data.display_dimension_count -lt 15) {
    throw 'Active drawing audit did not pass.'
}

Write-Host ''
Write-Host 'Exporting the verified Workspace drawing to a new PDF...'
$pdf = Invoke-ConnectorWorker 'sw_export_workspace_pdf' ([ordered]@{})
if ([string]$pdf.connector_version -ne '2.2.2' -or
    [string]$pdf.verification.status -ne 'PASS' -or
    -not [bool]$pdf.source_drawing_unchanged) {
    throw 'Workspace PDF export verification did not pass.'
}
Assert-WorkspaceFile ([string]$pdf.file_path) '.PDF'

Write-Host ''
Write-Host 'PASS: immutable source, new parameter variant, drawing audit and PDF export passed.' -ForegroundColor Green
Write-Host "Unchanged source part: $($plate.file_path)"
Write-Host "New active variant: $($parameterChange.variant_path)"
Write-Host 'Verified variant dimensions: 140 x 90 x 8 mm'
Write-Host "Model dimensions marked for drawing: $($plate.driving_dimensions.total_marked_for_drawing)"
Write-Host "Drawing: $($drawing.file_path)"
Write-Host "Verified drawing display dimensions: $($drawing.verification.display_dimension_count)"
Write-Host "Audited drawing views: $($audit.data.referenced_model_view_count)"
Write-Host "PDF: $($pdf.file_path)"
Write-Host 'The drawing is a draft. Only existing model dimensions are imported; no tolerances are invented.' -ForegroundColor Yellow
Start-Process explorer.exe -ArgumentList "`"$workspace`""
Read-Host 'Press Enter to close'
