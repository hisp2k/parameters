$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'

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

Write-Host 'GUARDED EXISTING-FEATURE EDIT TEST' -ForegroundColor Cyan
Write-Host 'Creates one new test plate, reads its feature tree, changes only the exact'
Write-Host 'linear thickness dimension owned by its Boss feature, verifies and saves it.'
Write-Host ''

$plate = Invoke-ConnectorWorker 'sw_create_plate' ([ordered]@{
    length_mm = 120
    width_mm = 80
    thickness_mm = 6
    hole_diameter_mm = 10
    edge_offset_x_mm = 15
    edge_offset_y_mm = 15
})
if ([string]$plate.connector_version -ne '2.2.2' -or [string]$plate.verification.status -ne 'PASS') {
    throw 'The installed connector is not version 2.2.2 or plate creation failed.'
}

$opened = Invoke-ConnectorWorker 'sw_open_local_file' ([ordered]@{ file_path = [string]$plate.file_path })
if ([string]$opened.connector_version -ne '2.2.2' -or
    -not [string]::Equals([IO.Path]::GetFullPath([string]$opened.file_path),
        [IO.Path]::GetFullPath([string]$plate.file_path), [StringComparison]::OrdinalIgnoreCase)) {
    throw 'The test did not reopen the exact SLDPRT it had just created.'
}

$features = Invoke-ConnectorWorker 'sw_features' ([ordered]@{ offset = 0; limit = 100 })
$createdFullName = [string]$plate.driving_dimensions.extrusion.dimension_full_name
$identityParts = @($createdFullName -split '@')
if ([string]::IsNullOrWhiteSpace($createdFullName) -or $identityParts.Count -lt 2) {
    throw 'Plate creation did not return the exact extrusion dimension identity.'
}
$createdFeatureName = [string]$identityParts[1]
$candidates = @()
foreach ($feature in @($features.data.items)) {
    if ([string]$feature.feature_name -ne $createdFeatureName -or
        [string]$feature.feature_type -ne 'Extrusion' -or [bool]$feature.suppressed) { continue }
    foreach ($dimension in @($feature.dimensions)) {
        $dimensionName = [string]$dimension.name
        if (($dimensionName -eq 'AI_Thickness' -or $dimensionName -eq 'D1') -and
            [Math]::Abs([double]$dimension.value_mm - 6.0) -le 0.001 -and
            [bool]$dimension.editable_by_feature_tool) {
            $candidates += [pscustomobject]@{ Feature = $feature; Dimension = $dimension }
        }
    }
}
if ($candidates.Count -ne 1) {
    $reportRoot = Join-Path $env:LOCALAPPDATA 'SolidWorksCodex\Reports'
    [IO.Directory]::CreateDirectory($reportRoot) | Out-Null
    $reportPath = Join-Path $reportRoot ('feature_edit_diagnostic_' +
        [DateTime]::Now.ToString('yyyyMMdd_HHmmss') + '.json')
    $diagnostic = [ordered]@{
        connector_version = '2.2.2'
        created_file = [string]$plate.file_path
        created_dimension_full_name = $createdFullName
        expected_feature_name = $createdFeatureName
        candidate_count = $candidates.Count
        sw_features_response = $features
    }
    $diagnosticJson = $diagnostic | ConvertTo-Json -Depth 20
    [IO.File]::WriteAllText($reportPath, $diagnosticJson, (New-Object Text.UTF8Encoding($false)))
    Write-Host ''
    Write-Host "DIAGNOSTIC REPORT: $reportPath" -ForegroundColor Yellow
    Write-Host 'Attach this JSON file. It contains the exact live feature and parameter responses.' -ForegroundColor Yellow
    throw "Expected one 6 mm editable depth parameter (AI_Thickness or native D1) under the exact created Extrusion; found $($candidates.Count)."
}
$target = $candidates[0]

Write-Host ''
Write-Host "Changing $($target.Feature.feature_name) / $($target.Dimension.full_name): 6 -> 9 mm..."
$changed = Invoke-ConnectorWorker 'sw_set_feature_dimensions' ([ordered]@{
    feature_name = [string]$target.Feature.feature_name
    expected_feature_type = [string]$target.Feature.feature_type
    changes = @([ordered]@{
        full_name = [string]$target.Dimension.full_name
        expected_current_mm = 6
        new_value_mm = 9
    })
})
if ([string]$changed.connector_version -ne '2.2.2' -or
    [string]$changed.verification.status -ne 'PASS' -or
    -not [bool]$changed.verification.feature_identity_confirmed -or
    [int]$changed.change_count -ne 1 -or
    -not (Test-Path -LiteralPath ([string]$changed.backup_path) -PathType Leaf)) {
    throw 'The guarded existing-feature edit did not pass all checks.'
}

$part = Invoke-ConnectorWorker 'sw_part' ([ordered]@{})
$sizes = @($part.data.bounding_box.size_xyz.value)
if ($sizes.Count -ne 3 -or [Math]::Abs([double]$sizes[2] - 9.0) -gt 0.05) {
    throw 'The edited test plate thickness is not approximately 9 mm.'
}

Write-Host ''
Write-Host 'PASS: exact Extrusion feature identity, owned linear dimension, backup, rebuild, geometry and save passed.' -ForegroundColor Green
Write-Host "Changed test part: $($changed.file_path)"
Write-Host "Automatic backup: $($changed.backup_path)"
Read-Host 'Press Enter to close'
