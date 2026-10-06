param([string]$ConnectorPath = (Join-Path $PSScriptRoot 'SolidWorksLocal.exe'))
$ErrorActionPreference = 'Stop'
$passed = 0
$failures = New-Object 'System.Collections.Generic.List[string]'
function Assert($Condition, [string]$Name) {
    if ($Condition) { $script:passed++ } else { $script:failures.Add($Name) }
}
function Fault-Code([scriptblock]$Action) {
    try { & $Action | Out-Null } catch {
        $e = $_.Exception
        while ($e.InnerException) { $e = $e.InnerException }
        $f = $e.GetType().GetField('Code', [Reflection.BindingFlags]'Instance,NonPublic')
        if ($f) { return $f.GetValue($e) }
        return $e.GetType().Name
    }
    return 'NO_FAULT'
}
Add-Type -Path (Join-Path $PSScriptRoot 'tests\AssemblyReadFixtures.cs')
$fixtureAssembly = [SolidWorks.Interop.sldworks.IModelDoc2].Assembly
$assembly = [Reflection.Assembly]::LoadFrom((Resolve-Path -LiteralPath $ConnectorPath).Path)
$type = $assembly.GetType('SolidWorksLocal.SolidWorksReader', $true)
$flags = [Reflection.BindingFlags]'Instance,NonPublic'
function Invoke-Reader($f, [string]$Method, [object[]]$Arguments = @()) {
    for ($i=0; $i -lt $Arguments.Count; $i++) {
        if ($null -ne $Arguments[$i]) { $Arguments[$i] = $Arguments[$i].PSObject.BaseObject }
    }
    return $type.GetMethod($Method, $flags).Invoke($f.Reader, $Arguments)
}
function Fixture {
    $doc = New-Object SolidWorks.Interop.sldworks.IPartDoc
    $doc.PathName = $testPath
    $doc.ReadOnly = $false
    $app = New-Object SolidWorks.Interop.sldworks.ISldWorks
    $app.IActiveDoc2 = $doc
    $reader = [Activator]::CreateInstance($type, $true)
    foreach ($entry in @{interop=$fixtureAssembly;swconst=$fixtureAssembly;app=$app}.GetEnumerator()) {
        $type.GetField($entry.Key,$flags).SetValue($reader,$entry.Value)
    }
    return @{ Reader=$reader; Doc=$doc; App=$app }
}
function Change([string]$Name) {
    $t = $assembly.GetType('SolidWorksLocal.ManagedParameterChange', $true)
    $r = [Activator]::CreateInstance($t, $true)
    $t.GetField('FullName',$flags).SetValue($r,$Name)
    $t.GetField('ExpectedMm',$flags).SetValue($r,10.0)
    $t.GetField('RequestedMm',$flags).SetValue($r,20.0)
    return $r
}
function Arguments { return New-Object 'System.Collections.Generic.Dictionary[string,object]' }
function Parameter-Arguments {
    $argsMap=Arguments
    $change=Arguments
    $change.Add('full_name','AI_Thickness@Boss1@Fixture.SLDPRT')
    $change.Add('expected_current_mm',10.0)
    $change.Add('new_value_mm',20.0)
    $argsMap.Add('changes',[object[]]@($change.PSObject.BaseObject))
    return $argsMap
}
function Dimension([string]$Name, [string]$FullName, [int]$Code = 0) {
    $d = New-Object SolidWorks.Interop.sldworks.IDimension
    $d.Name=$Name; $d.FullName=$FullName; $d.TypeCode=$Code
    return $d
}
$testDir = Join-Path ([IO.Path]::GetTempPath()) ('sw_write_safety_' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testDir | Out-Null
$testPath = Join-Path $testDir 'Fixture.SLDPRT'
New-Item -ItemType File -Path $testPath | Out-Null
try {
    foreach ($ro in @($true,$null)) {
        $f=Fixture
        $f.Doc.ReadOnly=$ro
        $code=Fault-Code { Invoke-Reader $f 'SaveLocalDocumentCore' @($true) }
        Assert ($code -eq 'DOCUMENT_NOT_WRITABLE') "save rejects readonly/unknown state, got $code"
        Assert ($f.Doc.SaveCalls -eq 0) 'no save on readonly/unknown document'
    }
    $f=Fixture
    $f.Doc.Dirty=$null
    $code=Fault-Code { Invoke-Reader $f 'SaveLocalDocumentCore' @($true) }
    Assert ($code -eq 'DOCUMENT_STATE_UNKNOWN') "save rejects unknown dirty state, got $code"
    Assert ($f.Doc.SaveCalls -eq 0) 'unknown dirty flag never reaches Save3'
    $f=Fixture
    $result=Invoke-Reader $f 'SaveLocalDocumentCore' @($true)
    Assert ($null -ne $result['backup_path'] -and (Test-Path -LiteralPath $result['backup_path'])) 'explicit save backs up even a clean document'
    $f=Fixture
    Invoke-Reader $f 'Document' | Out-Null
    $other=New-Object SolidWorks.Interop.sldworks.IModelDoc2
    $other.PathName=$testPath; $other.ReadOnly=$false
    $f.App.IActiveDoc2=$other
    $code=Fault-Code { Invoke-Reader $f 'SaveLocalDocumentCore' @($false) }
    Assert ($code -eq 'DOCUMENT_CHANGED') "save cannot retarget a different active object, got $code"
    Assert ($other.SaveCalls -eq 0 -and $f.Doc.SaveCalls -eq 0) 'neither document is saved after an active-object switch'
    $f=Fixture
    Invoke-Reader $f 'Document' | Out-Null
    $f.Doc.ConfigurationManager.ActiveConfiguration.Name='B'
    $code=Fault-Code { Invoke-Reader $f 'SaveLocalDocumentCore' @($false) }
    Assert ($code -eq 'CONFIGURATION_CHANGED' -and $f.Doc.SaveCalls -eq 0) "configuration switch blocks saving, got $code"

    foreach ($method in @('SetWorkspaceProperties','SetWorkspaceParameters','SetFeatureDimensions','SetGlobalVariable','CopyActiveToWorkspace','CreateDrawing','ExportWorkspacePdf')) {
        $f=Fixture
        $f.Doc.Dirty=$null
        if ($method -eq 'ExportWorkspacePdf') { $f.Doc.DocumentType=3 }
        $code=Fault-Code {
            if ($method -eq 'CopyActiveToWorkspace' -or $method -eq 'ExportWorkspacePdf') { Invoke-Reader $f $method }
            elseif ($method -eq 'SetWorkspaceParameters') { Invoke-Reader $f $method @((Parameter-Arguments)) }
            else { Invoke-Reader $f $method @((Arguments)) }
        }
        Assert ($code -in @('CLEAN_LOCAL_PART_REQUIRED','CLEAN_LOCAL_DRAWING_REQUIRED','CLEAN_SOURCE_REQUIRED','DOCUMENT_STATE_UNKNOWN')) "$method rejects unknown state before modifying/copying, got $code"
        Assert ($f.Doc.SaveCalls -eq 0) "$method does not save an unknown-state source"
    }

    $f=Fixture
    Invoke-Reader $f 'Document' | Out-Null
    $feature=New-Object SolidWorks.Interop.sldworks.IFeature
    $feature.Name='Boss1'
    $f.Doc.FirstFeature=$feature
    $foreign=Dimension 'D1' 'D1@Sketch1@Fixture.SLDPRT'
    $f.Doc.ModelParameter=$foreign
    $code=Fault-Code { Invoke-Reader $f 'ResolveOwnedFeatureDimension' @($feature,(Change $foreign.FullName)) }
    Assert ($code -eq 'FEATURE_DIMENSION_NOT_OWNED') "model-wide fallback cannot edit sketch dimensions via a boss, got $code"

    $feature.DisplayDimension=New-Object SolidWorks.Interop.sldworks.IDisplayDimension
    $feature.DisplayDimension.Dimension=$foreign
    $code=Fault-Code { Invoke-Reader $f 'ResolveOwnedFeatureDimension' @($feature,(Change $foreign.FullName)) }
    Assert ($code -eq 'FEATURE_DIMENSION_NOT_OWNED') "displayed foreign dimensions are not directly owned, got $code"
    $inventory=Invoke-Reader $f 'FeaturesData' @((Arguments))
    Assert (-not $inventory['items'][0]['dimensions'][0]['editable_by_feature_tool']) 'feature inventory cannot advertise foreign dimensions as editable'

    $feature.DisplayDimension=$null
    $own=Dimension 'AI_Thickness' 'AI_Thickness@Boss1@Fixture.SLDPRT' 1
    $f.Doc.ModelParameter=$own
    $feature.DirectDimension=$own
    $code=Fault-Code { Invoke-Reader $f 'ResolveOwnedFeatureDimension' @($feature,(Change $own.FullName)) }
    Assert ($code -eq 'FEATURE_DIMENSION_NOT_LINEAR') "AI name cannot override a known angular type for feature edits, got $code"
    $code=Fault-Code { Invoke-Reader $f 'ResolveManagedParameter' @((Change $own.FullName)) }
    Assert ($code -eq 'PARAMETER_NOT_LINEAR') "AI angular parameter cannot be written in millimetres, got $code"
    $inventory=Invoke-Reader $f 'ParametersData'
    Assert (-not $inventory['items'][0]['editable_by_connector']) 'known angular AI dimension is not advertised as linear'

    $own.TypeCode=0
    $code=Fault-Code { Invoke-Reader $f 'ResolveManagedParameter' @((Change $own.FullName)) }
    Assert ($code -eq 'NO_FAULT') "API parameter type zero is linear, got $code"
    $code=Fault-Code { $script:hiddenName=Invoke-Reader $f 'ManagedParameterFullName' @('AI_Thickness') }
    Assert ($code -eq 'NO_FAULT' -and $script:hiddenName -eq $own.FullName) 'variant resolves hidden parameters through the shared inventory'
    foreach ($typeCode in @(-1,0,1,2,3,99)) {
        $own.TypeCode=$typeCode
        $linear=$typeCode -eq 0
        $code=Fault-Code { Invoke-Reader $f 'ResolveOwnedFeatureDimension' @($feature,(Change $own.FullName)) }
        Assert ($code -eq $(if ($linear) {'NO_FAULT'} else {'FEATURE_DIMENSION_NOT_LINEAR'})) "owned dimension accepts only API linear type: $typeCode, got $code"
        $code=Fault-Code { Invoke-Reader $f 'ResolveManagedParameter' @((Change $own.FullName)) }
        Assert ($code -eq $(if ($linear) {'NO_FAULT'} else {'PARAMETER_NOT_LINEAR'})) "AI name cannot override parameter type: $typeCode, got $code"
        $inventory=Invoke-Reader $f 'ParametersData'
        $row=$inventory['items'][0]
        Assert ($row['editable_by_connector'] -eq $linear) "parameter inventory uses correct enum: $typeCode"
        Assert (($null -ne $row['value_mm']) -eq $linear) "non-linear values are never converted to mm: $typeCode"
    }
    $own.TypeCode=0
    $own.Name='D2'; $own.FullName='D2@Boss1@Fixture.SLDPRT'
    $feature.DisplayDimension=New-Object SolidWorks.Interop.sldworks.IDisplayDimension
    $feature.DisplayDimension.Dimension=$own
    $inventory=Invoke-Reader $f 'FeaturesData' @((Arguments))
    $row=$inventory['items'][0]['dimensions'][0]
    Assert ($row['editable_by_feature_tool'] -and $row['value_mm'] -eq 10) 'ordinary owned linear dimension needs no AI name heuristic'
    Assert ($row['dimension_type'] -eq 'swDimensionParamTypeDoubleLinear') 'dimension type label uses parameter enum, not display enum'
    $feature.TypeName='ProfileFeature'; $feature.Name='Sketch1'
    $own.FullName='D2@Sketch1@Fixture.SLDPRT'
    $inventory=Invoke-Reader $f 'FeaturesData' @((Arguments))
    $row=$inventory['items'][0]['dimensions'][0]
    Assert ($row['value_mm'] -eq 10 -and -not $row['editable_by_feature_tool']) 'ordinary sketch dimensions are readable in mm but remain read-only'
    $feature.Suppression=$null
    $code=Fault-Code { Invoke-Reader $f 'FeatureSuppressed' @($feature) }
    Assert ($code -eq 'FEATURE_SUPPRESSION_UNKNOWN') "unknown suppression is not treated as unsuppressed, got $code"

    foreach ($method in @('SetWorkspaceProperties','SetWorkspaceParameters','SetFeatureDimensions','SetGlobalVariable')) {
        $f=Fixture
        $f.Doc.ReadOnly=$true
        $argsMap=if ($method -eq 'SetWorkspaceParameters') { Parameter-Arguments } else { Arguments }
        $code=Fault-Code { Invoke-Reader $f $method @($argsMap) }
        Assert ($code -eq 'DOCUMENT_NOT_WRITABLE') "$method rejects readonly before mutation, got $code"
        Assert ($f.Doc.SaveCalls -eq 0 -and $f.Doc.RebuildCalls -eq 0) "$method cannot modify readonly memory"
    }
    $f=Fixture
    $f.Doc.RebuildSuccess=$false
    $code=Fault-Code { Invoke-Reader $f 'SetWorkspaceProperties' @((Arguments)) }
    Assert ($code -eq 'PROPERTY_REBUILD_FAILED' -and $f.Doc.SaveCalls -eq 0) "failed property rebuild must not save, got $code"

    foreach ($switch in @('configuration','document')) {
        $f=Fixture
        $dimension=Dimension 'AI_Thickness' 'AI_Thickness@Boss1@Fixture.SLDPRT'
        $f.Doc.ModelParameter=$dimension
        if ($switch -eq 'configuration') {
            $dimension.AfterSet={ $f.Doc.ConfigurationManager.ActiveConfiguration.Name='B' }.GetNewClosure()
        } else {
            $other=New-Object SolidWorks.Interop.sldworks.IPartDoc
            $other.PathName=$testPath; $other.ReadOnly=$false
            $dimension.AfterSet={ $f.App.IActiveDoc2=$other }.GetNewClosure()
        }
        $code=Fault-Code { Invoke-Reader $f 'SetWorkspaceParameters' @((Parameter-Arguments)) }
        $expected=if ($switch -eq 'configuration') { 'CONFIGURATION_CHANGED' } else { 'DOCUMENT_CHANGED' }
        Assert ($code -eq $expected) "actual parameter workflow detects $switch switch, got $code"
        Assert ($dimension.SetCalls -eq 1) 'rollback cannot write old values into a different configuration or active document'
        Assert ($f.Doc.SaveCalls -eq 0) 'switched target is not saved'
    }
    $f=Fixture
    $dimension=Dimension 'AI_Thickness' 'AI_Thickness@Boss1@Fixture.SLDPRT'
    $f.Doc.ModelParameter=$dimension
    $result=Invoke-Reader $f 'SetWorkspaceParameters' @((Parameter-Arguments))
    Assert ($result['verification']['status'] -eq 'PASS' -and $f.Doc.SaveCalls -eq 1) 'unchanged writable target still completes normal parameter workflow'
    Assert ($dimension.SetCalls -eq 1 -and $dimension.Value -eq 0.02) 'normal write stores millimetres as metres exactly once'
    Assert (Test-Path -LiteralPath $result['backup_path']) 'normal parameter write retains pre-change backup'
} finally {
    # Only remove this test's own uniquely named scratch files, never user CAD.
    Get-ChildItem -LiteralPath $testDir -File | Remove-Item -Force
    Remove-Item -LiteralPath $testDir
}
if ($failures.Count) {
    $failures | ForEach-Object { Write-Host "FAIL: $_" }
    throw "$($failures.Count) write-safety regressions failed; $passed passed."
}
Write-Host "PASS: $passed write-safety regression assertions. No live COM calls."
