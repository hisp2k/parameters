param(
 [Parameter(Mandatory=$true)][string]$TestRoot,
 [Parameter(Mandatory=$true)][string]$SourceAssembly,
 [Parameter(Mandatory=$true)][string]$SourcePart,
 [Parameter(Mandatory=$true)][string]$FeatureName,
 [string]$DimensionName='D1',
 [double]$ExpectedInitialMm=4,
 [double]$NewValueMm=5,
 [string]$ConnectorPath='',
 [string]$ResumeAfterChangeReport=''
)
$ErrorActionPreference='Stop'
if([string]::IsNullOrEmpty($ConnectorPath)) { $ConnectorPath=Join-Path $PSScriptRoot 'SolidWorksLocal.exe' }
$reportFolder=Join-Path $PSScriptRoot 'Reports'
[IO.Directory]::CreateDirectory($reportFolder)|Out-Null
$reportPath=Join-Path $reportFolder ('scoped_experiment_'+[DateTime]::Now.ToString('yyyyMMdd_HHmmss')+'_'+[Guid]::NewGuid().ToString('N').Substring(0,8)+'.json')
$report=[ordered]@{status='RUNNING';started_utc=[DateTime]::UtcNow.ToString('o');test_root=$TestRoot;source_assembly=$SourceAssembly;source_part=$SourcePart;connector_sha256=(Get-FileHash -LiteralPath $ConnectorPath).Hash;input=@{thickness_mm=$NewValueMm;kind='EXPERIMENT_INPUT_NOT_QUESTIONNAIRE_FORMULA'};steps=@();manufacturing_approved=$false}
function Save-Report { [IO.File]::WriteAllText($reportPath,($report|ConvertTo-Json -Depth 60),(New-Object Text.UTF8Encoding($false))) }
function Invoke-Connector([string]$Tool,[hashtable]$Arguments) {
 $payload=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($Arguments|ConvertTo-Json -Depth 12 -Compress)))
 $start=New-Object Diagnostics.ProcessStartInfo
 $start.FileName=(Resolve-Path -LiteralPath $ConnectorPath).Path
 $start.Arguments="--worker $Tool $payload"
 $start.UseShellExecute=$false;$start.CreateNoWindow=$true
 $start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
 $start.StandardOutputEncoding=New-Object Text.UTF8Encoding($false)
 $process=[Diagnostics.Process]::Start($start)
 try {
  $output=$process.StandardOutput.ReadToEndAsync();$errorOutput=$process.StandardError.ReadToEndAsync()
  if(-not $process.WaitForExit(90000)){$process.Kill();$process.WaitForExit();throw "Connector timed out: $Tool. Do not retry a mutation automatically."}
  $reply=$output.Result|ConvertFrom-Json
  $report.steps+=@{tool=$Tool;arguments=$Arguments;reply=$reply;completed_utc=[DateTime]::UtcNow.ToString('o')}
  Save-Report
  if($process.ExitCode -ne 0 -or -not $reply.ok){throw "$Tool : $($reply.error.code): $($reply.error.message)"}
  Write-Host "OK: $Tool $($Arguments.operation)"
  return $reply.data
 } finally {$process.Dispose()}
}
function Test-Document([string]$File,[string]$Operation) { Invoke-Connector 'sw_test_document' @{test_root=$TestRoot;file_path=$File;operation=$Operation} }
function Assert($Condition,[string]$Message) {if(-not $Condition){throw "Verification failed: $Message"}}
function Assert-Assembly($Audit,[string]$Part,[double]$Volume,[int]$Count) {
 Assert ($Audit.health.status -eq 'PASS' -and $Audit.health.mate_count -gt 0) 'assembly feature/mate codes must be clean and nonempty'
 $instances=@($Audit.components|Where-Object {$_.path -eq $Part})
 Assert ($instances.Count -eq $Count) 'plate instance count unchanged'
 foreach($instance in $Audit.components){
  Assert ($instance.resolved_configuration_match -and $instance.health.status -eq 'PASS') 'all component configurations and feature health are verified'
 }
 foreach($instance in $instances){
  Assert ($instance.geometry.solid_body_count -eq 1) 'plate instance contains one solid body'
  Assert ([Math]::Abs($instance.geometry.volume_m3/$Volume-1) -lt 0.000001) 'assembly instance has expected plate volume'
 }
}
try {
 $report.initial_document=Invoke-Connector 'sw_document' @{}
 if($ResumeAfterChangeReport){
  $previous=Get-Content -LiteralPath $ResumeAfterChangeReport -Raw -Encoding UTF8|ConvertFrom-Json
  Assert ($previous.test_root -eq $TestRoot -and $previous.source_assembly -eq $SourceAssembly -and $previous.source_part -eq $SourcePart -and $previous.input.thickness_mm -eq $NewValueMm) 'resume scope and input match'
  Assert ($previous.change.verification.status -eq 'PASS') 'resume requires a recorded successful dimension change'
  $report.resumed_from=@{path=(Resolve-Path -LiteralPath $ResumeAfterChangeReport).Path;sha256=(Get-FileHash -LiteralPath $ResumeAfterChangeReport).Hash;previous_steps=$previous.steps}
  $report.pack=$previous.pack;$report.change=$previous.change;$report.dimension_full_name=$previous.dimension_full_name
  $assembly=$previous.variant_assembly;$part=$previous.variant_part
  $report.variant_assembly=$assembly;$report.variant_part=$part
  $volumeBefore=$previous.change.verification.volume_before_m3
  $expectedVolume=$volumeBefore*$NewValueMm/$ExpectedInitialMm
  $baselineAssembly=@($previous.steps|Where-Object {$_.tool -eq 'sw_test_document' -and $_.arguments.operation -eq 'rebuild_save'})[0].reply.data
  $instances=@($baselineAssembly.audit.components|Where-Object {$_.path -eq $part}).Count
  Assert ($instances -gt 0) 'recorded baseline has target plate instances'
  Test-Document $part 'open'|Out-Null
  $current=Invoke-Connector 'sw_features' @{offset=0;limit=100}
  $currentDimension=@($current.data.items.dimensions|Where-Object {$_.full_name -ceq $report.dimension_full_name})
  Assert ($currentDimension.Count -eq 1 -and [Math]::Abs($currentDimension[0].value_mm-$NewValueMm) -le 0.001) 'resume does not repeat an already applied edit'
 } else {
 $report.pack=Invoke-Connector 'sw_test_pack_and_go' @{test_root=$TestRoot;file_path=$SourceAssembly}
 $assembly=$report.pack.assembly_path
 $matches=@($report.pack.mapping|Where-Object {$_.source -eq $SourcePart})
 Assert ($matches.Count -eq 1) 'one exact source part in Pack and Go mapping'
 $part=$matches[0].copy
 $report.variant_assembly=$assembly;$report.variant_part=$part
 Test-Document $assembly 'open'|Out-Null
 $baselineAssembly=Test-Document $assembly 'rebuild_save'
 Test-Document $part 'open'|Out-Null
 $baseline=Test-Document $part 'audit'
 Assert ($baseline.audit.health.status -eq 'PASS' -and $baseline.audit.geometry.solid_body_count -eq 1) 'clean baseline part with one body'
 $features=Invoke-Connector 'sw_features' @{offset=0;limit=100}
 Assert (-not $features.partial -and $features.data.total -le 100) 'complete feature inventory'
 $feature=@($features.data.items|Where-Object {$_.feature_name -ceq $FeatureName})
 Assert ($feature.Count -eq 1) 'exact unique feature identity'
 $dimension=@($feature[0].dimensions|Where-Object {$_.name -ceq $DimensionName})
 Assert ($dimension.Count -eq 1 -and $dimension[0].editable_by_feature_tool -and [Math]::Abs($dimension[0].value_mm-$ExpectedInitialMm) -le 0.001) 'exact editable driving dimension at expected initial value'
 $volumeBefore=$baseline.audit.geometry.volume_m3
 $expectedVolume=$volumeBefore*$NewValueMm/$ExpectedInitialMm
 $instances=@($baselineAssembly.audit.components|Where-Object {$_.path -eq $part}).Count
 Assert ($instances -gt 0) 'part participates in copied assembly'
 Assert-Assembly $baselineAssembly.audit $part $volumeBefore $instances
 $report.dimension_full_name=$dimension[0].full_name
 $report.change=Invoke-Connector 'sw_set_feature_dimensions' @{feature_name=$FeatureName;expected_feature_type=$feature[0].feature_type;changes=@(@{full_name=$dimension[0].full_name;expected_current_mm=$ExpectedInitialMm;new_value_mm=$NewValueMm})}
 Assert ($report.change.verification.status -eq 'PASS') 'guarded dimension edit/rebuild/save'
 }
 $changed=Test-Document $part 'audit'
 Assert ($changed.audit.health.status -eq 'PASS' -and $changed.audit.geometry.solid_body_count -eq 1) 'changed part feature health and body count'
 Assert ([Math]::Abs($changed.audit.geometry.volume_m3/$expectedVolume-1) -lt 0.000001) 'expected thickness/volume relation'
 Test-Document $assembly 'open'|Out-Null
 $changedAssembly=Test-Document $assembly 'rebuild_save'
 Assert-Assembly $changedAssembly.audit $part $expectedVolume $instances
 Test-Document $assembly 'close'|Out-Null
 $reopened=Test-Document $part 'reopen'
 Assert ($reopened.unloaded_before_open -and $reopened.open_status -eq 'OPENED_CLEAN') 'true unload and clean disk reopen'
 Assert ($reopened.audit.health.status -eq 'PASS' -and -not $reopened.audit.has_unsaved_changes) 'reopened saved part is clean'
 $persisted=Invoke-Connector 'sw_features' @{offset=0;limit=100}
 $persistedDimension=@($persisted.data.items.dimensions|Where-Object {$_.full_name -ceq $report.dimension_full_name})
 Assert ($persistedDimension.Count -eq 1 -and [Math]::Abs($persistedDimension[0].value_mm-$NewValueMm) -le 0.001) 'new dimension persisted on disk'
 $reloadedAssembly=Test-Document $assembly 'open'
 Assert-Assembly $reloadedAssembly.audit $part $expectedVolume $instances
 $report.verification=@{new_dimension_mm=$persistedDimension[0].value_mm;volume_before_m3=$volumeBefore;volume_after_m3=$reopened.audit.geometry.volume_m3;plate_instances=$instances;mates=$reloadedAssembly.audit.health.mate_count;assembly_feature_errors=$reloadedAssembly.audit.health.error_count;assembly_feature_warnings=$reloadedAssembly.audit.health.warning_count;true_disk_reopen=$true;input_relation='plate_thickness_mm -> native extrusion D1 -> plate volume -> both component instances';assembly_impact='COPIED_NATIVE_SUBASSEMBLY_ONLY';original_root_assembly_rebuilt=$false}
 $report.status='LIVE_PASS'
} catch {$report.status='LIVE_FAIL';$report.error=$_.Exception.Message;throw} finally {
 $report.finished_utc=[DateTime]::UtcNow.ToString('o');Save-Report
 Write-Host "REPORT: $reportPath"
 Write-Host "RESULT: $($report.status)"
}
