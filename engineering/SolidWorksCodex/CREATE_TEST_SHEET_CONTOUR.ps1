$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$partName = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('0JrQvtC90YLRgNC+0LvRjNC90YvQuSDRidC40YIg0YEg0LrQvtC90YLRg9GA0L7QvA=='))

function Line {
    param([double]$x1, [double]$y1, [double]$x2, [double]$y2)
    [ordered]@{ type='line'; start_x_mm=[double]$x1; start_y_mm=[double]$y1; end_x_mm=[double]$x2; end_y_mm=[double]$y2 }
}
function Arc {
    param([double]$x1, [double]$y1, [double]$x2, [double]$y2, [double]$cx, [double]$cy)
    [ordered]@{ type='arc'; start_x_mm=[double]$x1; start_y_mm=[double]$y1; end_x_mm=[double]$x2; end_y_mm=[double]$y2; center_x_mm=[double]$cx; center_y_mm=[double]$cy; clockwise=$false }
}

$outer = @(
    (Line (-235.0) (-110.0) 235.0 (-110.0)), (Arc 235.0 (-110.0) 250.0 (-95.0) 235.0 (-95.0)),
    (Line 250.0 (-95.0) 250.0 95.0), (Arc 250.0 95.0 235.0 110.0 235.0 95.0),
    (Line 235.0 110.0 (-235.0) 110.0), (Arc (-235.0) 110.0 (-250.0) 95.0 (-235.0) 95.0),
    (Line (-250.0) 95.0 (-250.0) (-95.0)), (Arc (-250.0) (-95.0) (-235.0) (-110.0) (-235.0) (-95.0))
)
$window = @(
    (Line (-70.0) (-50.0) 70.0 (-50.0)), (Arc 70.0 (-50.0) 80.0 (-40.0) 70.0 (-40.0)),
    (Line 80.0 (-40.0) 80.0 0.0), (Arc 80.0 0.0 70.0 10.0 70.0 0.0),
    (Line 70.0 10.0 (-70.0) 10.0), (Arc (-70.0) 10.0 (-80.0) 0.0 (-70.0) 0.0),
    (Line (-80.0) 0.0 (-80.0) (-40.0)), (Arc (-80.0) (-40.0) (-70.0) (-50.0) (-70.0) (-40.0))
)
$plan = [ordered]@{
    plan_version = '1'
    thickness_mm = 3
    outer_contour = [ordered]@{ segments = $outer }
    inner_contours = @([ordered]@{ segments = $window })
    linear_hole_patterns = @(
        [ordered]@{ start_x_mm=[double](-200); start_y_mm=[double]70; step_x_mm=[double]80; step_y_mm=[double]0; count=6; diameter_mm=[double]9 }
    )
    properties = [ordered]@{ designation='AI.SHEET.001'; name=$partName }
    material = 'AISI 304'
}

$json = $plan | ConvertTo-Json -Depth 14 -Compress
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
Write-Host 'SHEET-CONTOUR TEST: true lines/arcs, rounded outer edge, rounded inner window and six-hole linear pattern.'
Write-Host 'A new 500 x 220 x 3 mm control part will be created in local Workspace.'
Write-Host 'Existing documents will not be saved or edited.'
Write-Host ''
$raw = (& $exe --worker sw_create_sheet_from_contours $payload 2>&1 | Out-String).Trim()
Write-Host $raw
$result = $raw | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $result.ok) { throw 'SOLIDWORKS sheet-contour creation failed.' }
$data = $result.data
$path = [string]$data.file_path
if ([string]$data.connector_version -ne '2.2.2') { throw 'The installed connector is not version 2.2.2.' }
if (-not (Test-Path -LiteralPath $path)) { throw "Generated SLDPRT does not exist: $path" }
if ([string]$data.verification.status -ne 'PASS' -or [string]$data.verification.topology.status -ne 'PASS') {
    throw 'Volume or topology verification did not pass.'
}
$topology = $data.verification.topology
if ([int]$topology.solid_body_count -ne 1 -or [int]$topology.outer_segment_count -ne 8 -or
    [int]$topology.inner_contour_count -ne 1 -or [int]$topology.through_hole_count -ne 6) {
    throw 'Unexpected body, segment, cutout or hole count.'
}
$envelope = @($data.plan.calculated.envelope_xyz_mm)
if ($envelope.Count -ne 3 -or [Math]::Abs(([double]$envelope[0])-500) -gt 0.01 -or
    [Math]::Abs(([double]$envelope[1])-220) -gt 0.01 -or [Math]::Abs(([double]$envelope[2])-3) -gt 0.001) {
    throw 'The verified envelope is not 500 x 220 x 3 mm.'
}
Write-Host ''
Write-Host 'PASS: ordered contour, true arcs, inner cutout, six-hole pattern, volume and B-rep topology passed.' -ForegroundColor Green
Start-Process explorer.exe -ArgumentList "/select,`"$path`""
Read-Host 'Press Enter to close'
