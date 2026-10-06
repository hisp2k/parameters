param(
    [string]$ConnectorPath = (Join-Path $PSScriptRoot 'SolidWorksLocal.exe'),
    [string]$InteropPath
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'DependencyGraph.ps1')
$script:passed = 0
function Assert($Condition, [string]$Name) {
    if (-not $Condition) { throw "FAIL: $Name" }
    $script:passed++
}
function Assert-Throws([scriptblock]$Action, [string]$Name) {
    $threw = $false
    try { & $Action | Out-Null } catch { $threw = $true }
    Assert $threw $Name
}
function Assert-Fault([scriptblock]$Action, [string]$Code, [string]$Name) {
    $actualCode = $null
    try { & $Action | Out-Null } catch {
        $exception = $_.Exception
        while ($null -ne $exception.InnerException) { $exception = $exception.InnerException }
        $field = $exception.GetType().GetField('Code', [Reflection.BindingFlags]'Instance,NonPublic')
        if ($null -ne $field) { $actualCode = $field.GetValue($exception) }
    }
    Assert ($actualCode -eq $Code) "$Name (expected $Code, got $actualCode)"
}
function Dependencies([object[]]$Entries) {
    return Get-DependencyPaths ([pscustomobject]@{ data = [pscustomobject]@{
        api_call_status = 'OK'; dependencies = $Entries
    } })
}

$root = Get-DependencyPathKey 'C:\Pilot\Root.SLDASM'
$frame = Get-DependencyPathKey 'C:\Pilot\Frame.SLDASM'
$child = Get-DependencyPathKey 'C:\Pilot\Child.SLDASM'
$empty = Dependencies @()
Assert ($empty.Count -eq 0) 'empty dependency set preserves its type'
$foreign = Dependencies @('Frame', 'C:\Other\Frame.SLDASM')
Assert (-not $foreign.Contains($frame)) 'same filename in another directory is not the candidate'
Assert ($foreign.Count -eq 1) 'one dependency remains a HashSet, not a scalar'
$graph = @{}
$graph[$root] = $foreign
$graph[$frame] = $empty
Assert (-not (Get-ReachableDependencyPaths $graph $root).Contains($frame)) 'foreign namesake cannot create graph reachability'
$graph[$root] = Dependencies @('Frame', 'c:/PILOT/temp/../Frame.SLDASM')
$graph[$frame] = Dependencies @('Child', 'C:\Pilot\Child.SLDASM', 'Root', 'C:\Elsewhere\Root.SLDASM')
$graph[$child] = Dependencies @('Frame', 'C:\Pilot\Frame.SLDASM')
$reachable = Get-ReachableDependencyPaths $graph $root
Assert ($reachable.Count -eq 3 -and $reachable.Contains($child)) 'normalized direct and indirect paths with a cycle'
Assert (-not $graph[$frame].Contains($root)) 'foreign root namesake is not a reverse reference'
$reverse = Dependencies @('Root', 'C:\PILOT\Root.SLDASM')
Assert ($reverse.Contains($root)) 'actual reverse reference is detected'
Assert-Throws { Dependencies @('Frame') } 'incomplete API pairs fail closed'
Assert-Throws { Dependencies @('Frame', 'Frame.SLDASM') } 'relative references cannot be guessed'
Assert-Throws { Get-DependencyPathKey 'C:Frame.SLDASM' } 'drive-relative paths cannot be guessed'
Assert-Throws { Get-DependencyPaths ([pscustomobject]@{data = [pscustomobject]@{api_call_status='UNKNOWN'; dependencies=@()}}) } 'unknown API result cannot prove no dependencies'

Add-Type -Path (Join-Path $PSScriptRoot 'tests\AssemblyReadFixtures.cs')
$fixtureAssembly = [SolidWorks.Interop.sldworks.IComponent2].Assembly
$connector = [Reflection.Assembly]::LoadFrom((Resolve-Path -LiteralPath $ConnectorPath).Path)
$readerType = $connector.GetType('SolidWorksLocal.SolidWorksReader', $true)
$flags = [Reflection.BindingFlags]'Instance,NonPublic'
function New-ReaderFixture([string]$Referenced = 'A', [string]$Loaded = 'A') {
    $document = New-Object SolidWorks.Interop.sldworks.IPartDoc
    $document.ConfigurationManager.ActiveConfiguration.Name = $Loaded
    $component = New-Object SolidWorks.Interop.sldworks.IComponent2
    $component.Name2 = 'Part-1'
    $component.ReferencedConfiguration = $Referenced
    $component.Document = $document
    $model = New-Object SolidWorks.Interop.sldworks.IAssemblyDoc
    $model.Component = $component
    $reader = [Activator]::CreateInstance($readerType, $true)
    foreach ($entry in @{interop=$fixtureAssembly; swconst=$fixtureAssembly; model=$model; kind=2}.GetEnumerator()) {
        $readerType.GetField($entry.Key, $flags).SetValue($reader, $entry.Value)
    }
    return @{ Reader=$reader; Document=$document; Component=$component }
}
function Read-Details($Fixture) {
    $arguments = New-Object 'System.Collections.Generic.Dictionary[string,object]'
    $arguments.Add('instance_id', 'Part-1')
    return $readerType.GetMethod('ComponentDetails', $flags).Invoke($Fixture.Reader, @($arguments.PSObject.BaseObject))['component']
}
foreach ($virtual in @($true, $false)) {
    $fixture = New-ReaderFixture
    $fixture.Component.IsVirtual = $virtual
    $details = Read-Details $fixture
    Assert ($details['is_virtual'] -ceq $virtual) "component IsVirtual=$virtual"
    Assert ($details['mass_properties_status'] -eq 'VERIFIED' -and $details['mass_properties']['mass_kg'] -eq 2.0) 'matching configuration returns mass'
    Assert ($details['mass_properties']['configuration'] -eq 'A') 'mass identifies its configuration'
    $arguments = New-Object 'System.Collections.Generic.Dictionary[string,object]'
    $tree = $readerType.GetMethod('AssemblyTree', $flags).Invoke($fixture.Reader, @($arguments.PSObject.BaseObject))
    Assert ($tree['items'][0]['is_virtual'] -ceq $virtual) "tree IsVirtual=$virtual"
    Assert ($readerType.GetField('issues', $flags).GetValue($fixture.Reader).Count -eq 0) 'component and tree read without reflection errors'
}
foreach ($configurations in @(@('B','A'), @('','A'), @('A',''), @('',''))) {
    $fixture = New-ReaderFixture $configurations[0] $configurations[1]
    $details = Read-Details $fixture
    Assert ($null -eq $details['mass_properties'] -and $details['mass_properties_status'] -eq 'UNKNOWN') 'mismatched or unknown configuration withholds mass'
    Assert ($fixture.Document.Extension.MassReads -eq 0) 'guard prevents reading the wrong configuration mass'
    $issues = $readerType.GetField('issues', $flags).GetValue($fixture.Reader)
    Assert (@($issues | Where-Object { $_['field'] -eq 'component.mass_properties' }).Count -eq 1) 'withheld mass has a diagnostic reason'
}
$fixture = New-ReaderFixture
$fixture.Document.ChangeConfigurationDuringMassRead()
$details = Read-Details $fixture
Assert ($null -eq $details['mass_properties'] -and $details['mass_properties_status'] -eq 'UNKNOWN') 'configuration changed during read invalidates mass'
$fixture = New-ReaderFixture
$fixture.Component.Document = $null
Assert (-not (Read-Details $fixture)['resolved']) 'unloaded component remains unresolved'
$fixture = New-ReaderFixture
$fixture.Component.Suppressed = $true
Assert (-not (Read-Details $fixture)['resolved']) 'suppressed component remains unresolved'
$fixture = New-ReaderFixture
$equations = $readerType.GetMethod('EquationsData', $flags).Invoke($fixture.Reader, @())
for ($i = 0; $i -lt 3; $i++) {
    Assert ($equations['items'][$i]['configuration_option'] -eq $i+1) 'equation uses indexed GetConfigurationOption method'
    Assert ($null -eq $equations['items'][$i]['configuration_name'] -and $equations['items'][$i]['configuration_name_status'] -eq 'UNKNOWN') 'unsupported equation names remain explicitly unknown'
}
$scopeIssues = @($readerType.GetField('issues', $flags).GetValue($fixture.Reader) | Where-Object { $_['field'] -like 'equation.configuration*' })
Assert ($scopeIssues.Count -eq 0) 'no calls to nonexistent equation scope properties'

# OpenDoc6 handling: distinguish a genuine open failure (no document) from a document SOLIDWORKS
# actually opened while reporting load errors. Program.RequireLocalFixedPath performs real
# filesystem/drive checks that cannot be mocked, so these tests use one real, harmless local file.
$openTestPath = Join-Path ([IO.Path]::GetTempPath()) ('sw_regression_open_test_' + [Guid]::NewGuid().ToString('N') + '.SLDASM')
New-Item -Path $openTestPath -ItemType File -Force | Out-Null
$openPartTestPath = [IO.Path]::ChangeExtension($openTestPath, '.SLDPRT')
New-Item -Path $openPartTestPath -ItemType File -Force | Out-Null
try {
    function New-OpenReaderFixture {
        $sw = New-Object SolidWorks.Interop.sldworks.ISldWorks
        $reader = [Activator]::CreateInstance($readerType, $true)
        foreach ($entry in @{interop=$fixtureAssembly; swconst=$fixtureAssembly; app=$sw}.GetEnumerator()) {
            $readerType.GetField($entry.Key, $flags).SetValue($reader, $entry.Value)
        }
        return @{ Reader = $reader; App = $sw }
    }
    function Invoke-OpenLocalPath($Fixture, [string]$Path = $openTestPath, [bool]$AllowAssembly = $true, [bool]$RequestReadOnly = $true, [bool]$RequireCleanLoad = $false) {
        return $readerType.GetMethod('OpenLocalPath', $flags).Invoke($Fixture.Reader, @($Path, $AllowAssembly, $RequestReadOnly, $RequireCleanLoad))
    }

    $fixture = New-OpenReaderFixture
    $fixture.App.OpenDocResult = $null
    $fixture.App.OpenDocErrors = 2
    Assert-Throws { Invoke-OpenLocalPath $fixture } 'OpenDoc6 returning no document at all is a genuine OPEN_FAILED'

    $fixture = New-OpenReaderFixture
    $doc = New-Object SolidWorks.Interop.sldworks.IModelDoc2
    $doc.DocumentType = 2
    $doc.PathName = $openTestPath; $doc.Title = 'RegressionOpenTest'; $doc.ReadOnly = $true
    $fixture.App.OpenDocResult = $doc
    $fixture.App.OpenDocErrors = 2
    $fixture.App.OpenDocWarnings = 0
    $fixture.App.ActivateResult = $doc
    $result = Invoke-OpenLocalPath $fixture
    Assert ($result['errors'] -eq 2) 'a document actually opened with load errors preserves the exact errors code instead of being discarded'
    Assert ($result['open_status'] -eq 'OPENED_WITH_LOAD_ERRORS') 'a load-error open is never reported as a clean/PASS open_status'
    Assert ($result['path'] -eq $openTestPath) 'a load-error open still runs the real path/type verification'
    Assert ($result['confirmed_read_only'] -eq $true) 'a load-error open still confirms the real read-only state instead of assuming it'
    Assert ($fixture.App.OpenDocCallCount -eq 1) 'a load-error open calls OpenDoc6 exactly once, no silent retry'

    $fixture = New-OpenReaderFixture
    $doc2 = New-Object SolidWorks.Interop.sldworks.IModelDoc2
    $doc2.DocumentType = 2
    $doc2.PathName = $openTestPath; $doc2.Title = 'RegressionOpenTestClean'; $doc2.ReadOnly = $true
    $fixture.App.OpenDocResult = $doc2
    $fixture.App.OpenDocErrors = 0
    $fixture.App.ActivateResult = $doc2
    $result = Invoke-OpenLocalPath $fixture
    Assert ($result['open_status'] -eq 'OPENED_CLEAN') 'an open with errors=0 is reported as OPENED_CLEAN, distinct from a load-error open'

    $fixture = New-OpenReaderFixture
    $already = New-Object SolidWorks.Interop.sldworks.IModelDoc2
    $already.DocumentType = 2
    $already.PathName = $openTestPath; $already.Title = 'RegressionOpenTestReused'; $already.ReadOnly = $true
    $fixture.App.AlreadyOpenDocument = $already
    $fixture.App.ActivateResult = $already
    $result = Invoke-OpenLocalPath $fixture
    Assert ($result['reused_already_open_read_only'] -eq $true) 'an already-open, confirmed-read-only document is reused rather than reopened'
    Assert ($result['open_status'] -eq 'REUSED_ALREADY_OPEN') 'the reuse path reports REUSED_ALREADY_OPEN, distinct from a fresh OpenDoc6 result'
    Assert ($fixture.App.OpenDocCallCount -eq 0) 'the reuse path never calls OpenDoc6 again'

    $fixture = New-OpenReaderFixture
    $already2 = New-Object SolidWorks.Interop.sldworks.IModelDoc2
    $already2.ReadOnly = $false
    $fixture.App.AlreadyOpenDocument = $already2
    Assert-Throws { Invoke-OpenLocalPath $fixture } 'an already-open document not confirmed read-only is never silently reused'

    $fixture = New-OpenReaderFixture
    $docNoTitle = New-Object SolidWorks.Interop.sldworks.IModelDoc2
    $docNoTitle.Title = ''
    $fixture.App.OpenDocResult = $docNoTitle
    $fixture.App.OpenDocErrors = 0
    Assert-Throws { Invoke-OpenLocalPath $fixture } 'a document OpenDoc6 returned but whose title cannot be read is a genuine failure, not a silent activation'

    $fixture = New-OpenReaderFixture
    $wrongPathDoc = New-Object SolidWorks.Interop.sldworks.IModelDoc2
    $wrongPathDoc.PathName = (Join-Path ([IO.Path]::GetTempPath()) 'not_the_requested_file.SLDASM')
    $wrongPathDoc.Title = 'WrongPath'
    $fixture.App.OpenDocResult = $wrongPathDoc
    $fixture.App.OpenDocErrors = 2
    $fixture.App.ActivateResult = $wrongPathDoc
    Assert-Throws { Invoke-OpenLocalPath $fixture } 'a load-error open that activates the wrong document still fails local-file verification'

    foreach ($readOnly in @($true, $false)) {
        $fixture = New-OpenReaderFixture
        $doc = New-Object SolidWorks.Interop.sldworks.IModelDoc2
        $doc.PathName = $openPartTestPath; $doc.ReadOnly = $readOnly
        $fixture.App.OpenDocResult = $doc
        $fixture.App.OpenDocWarnings = 64
        $result = Invoke-OpenLocalPath $fixture $openPartTestPath $false $readOnly
        Assert ($result['open_status'] -eq 'OPENED_WITH_WARNINGS' -and $result['warnings'] -eq 64) 'warnings are preserved and never labelled OPENED_CLEAN'
    }
    $fixture.App.OpenDocErrors = 2
    Assert-Fault { Invoke-OpenLocalPath $fixture $openPartTestPath $false $false } 'OPEN_LOAD_ERRORS' 'ordinary part open rejects load errors'

    $fixture = New-OpenReaderFixture
    $doc = New-Object SolidWorks.Interop.sldworks.IModelDoc2
    $doc.PathName = $openPartTestPath; $doc.ReadOnly = $true
    $fixture.App.OpenDocResult = $doc
    $fixture.App.OpenDocErrors = 2
    $fixture.App.OpenDocWarnings = 64
    $result = Invoke-OpenLocalPath $fixture $openPartTestPath $false $true
    Assert ($result['open_status'] -eq 'OPENED_WITH_LOAD_ERRORS' -and $result['errors'] -eq 2 -and $result['warnings'] -eq 64) 'read-only partial load preserves both bitmasks with error status taking precedence'

    foreach ($codes in @(@(2,0), @(0,64), @(2,64))) {
        $fixture = New-OpenReaderFixture
        $doc = New-Object SolidWorks.Interop.sldworks.IModelDoc2
        $doc.PathName = $openPartTestPath
        $fixture.App.OpenDocResult = $doc
        $fixture.App.OpenDocErrors = $codes[0]
        $fixture.App.OpenDocWarnings = $codes[1]
        $expectedCode = if ($codes[0] -ne 0) { 'OPEN_LOAD_ERRORS' } else { 'OPEN_LOAD_WARNINGS' }
        Assert-Fault { Invoke-OpenLocalPath $fixture $openPartTestPath $false $false $true } $expectedCode 'modification policy rejects every non-clean load'
        Assert ($null -eq $fixture.App.LastActivateName) 'rejected modification load is not activated'
        $arguments = New-Object 'System.Collections.Generic.Dictionary[string,object]'
        $arguments.Add('source_path', $openPartTestPath)
        $change = New-Object 'System.Collections.Generic.Dictionary[string,object]'
        $change.Add('full_name', 'AI_Length@Sketch1@Part.SLDPRT')
        $change.Add('expected_current_mm', 10)
        $change.Add('new_value_mm', 20)
        $arguments.Add('changes', [object[]]@($change.PSObject.BaseObject))
        Assert-Fault { $readerType.GetMethod('CreateParameterVariant', $flags).Invoke($fixture.Reader, @($arguments.PSObject.BaseObject)) } $expectedCode 'actual variant workflow stops at the source load before copying or editing'
    }
    $fixture.App.OpenDocErrors = 0
    $fixture.App.OpenDocWarnings = 0
    $result = Invoke-OpenLocalPath $fixture $openPartTestPath $false $false $true
    Assert ($result['open_status'] -eq 'OPENED_CLEAN') 'modification policy still accepts a clean part load'

    foreach ($readOnly in @($false, $null)) {
        $fixture = New-OpenReaderFixture
        $doc = New-Object SolidWorks.Interop.sldworks.IModelDoc2
        $doc.PathName = $openTestPath; $doc.DocumentType = 2; $doc.ReadOnly = $readOnly
        $fixture.App.OpenDocResult = $doc
        $fixture.App.OpenDocErrors = 2
        Assert-Fault { Invoke-OpenLocalPath $fixture } 'READ_ONLY_NOT_CONFIRMED' 'fresh partial load must confirm actual read-only access'
    }
    $fixture = New-OpenReaderFixture
    $doc = New-Object SolidWorks.Interop.sldworks.IModelDoc2
    $doc.PathName = $openTestPath; $doc.DocumentType = 1; $doc.ReadOnly = $true
    $fixture.App.OpenDocResult = $doc
    Assert-Fault { Invoke-OpenLocalPath $fixture } 'LOCAL_FILE_TYPE_MISMATCH' 'matching path cannot hide an incorrect actual document type'
} finally {
    Remove-Item -LiteralPath $openTestPath,$openPartTestPath -Force -ErrorAction SilentlyContinue
}

if ($InteropPath) {
    $installed = [Reflection.Assembly]::LoadFrom((Resolve-Path -LiteralPath $InteropPath).Path)
    $componentApi = $installed.GetType('SolidWorks.Interop.sldworks.IComponent2', $true)
    $equationApi = $installed.GetType('SolidWorks.Interop.sldworks.IEquationMgr', $true)
    $sldWorksApi = $installed.GetType('SolidWorks.Interop.sldworks.ISldWorks', $true)
    Assert ($componentApi.GetProperty('IsVirtual').PropertyType -eq [bool]) 'installed API exposes IsVirtual as a boolean property'
    Assert ($equationApi.GetMethod('GetConfigurationOption').GetParameters()[0].ParameterType -eq [int]) 'installed API exposes GetConfigurationOption(index)'
    Assert ($null -ne $sldWorksApi.GetMethod('OpenDoc6')) 'installed API exposes ISldWorks.OpenDoc6'
    $constants = [Reflection.Assembly]::LoadFrom((Join-Path (Split-Path $InteropPath) 'SolidWorks.Interop.swconst.dll'))
    $parameterTypes = $constants.GetType('SolidWorks.Interop.swconst.swDimensionParamType_e', $true)
    Assert ([int][Enum]::Parse($parameterTypes,'swDimensionParamTypeDoubleLinear') -eq 0) 'installed API parameter linear type is zero'
    Assert ([int][Enum]::Parse($parameterTypes,'swDimensionParamTypeDoubleAngular') -eq 1) 'installed API parameter angular type is one'
    Assert ([int][Enum]::Parse($parameterTypes,'swDimensionParamTypeInteger') -eq 2) 'installed API parameter integer type is two'
    Assert ([int][Enum]::Parse($parameterTypes,'swDimensionParamTypeUnknown') -eq -1) 'installed API parameter unknown type is minus one'
}
$messages = @(
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"assembly-regression","version":"1"}}}',
    '{"jsonrpc":"2.0","method":"notifications/initialized"}',
    '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}',
    '{invalid-json',
    '{"jsonrpc":"2.0","id":3,"method":"ping","params":{}}',
    '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"sw_component_details","arguments":{}}}'
)
$start = New-Object Diagnostics.ProcessStartInfo
$start.FileName = (Resolve-Path -LiteralPath $ConnectorPath).Path
$start.Arguments = '--stdio'
$start.UseShellExecute = $false
$start.CreateNoWindow = $true
$start.RedirectStandardInput = $true
$start.RedirectStandardOutput = $true
$start.RedirectStandardError = $true
$start.StandardOutputEncoding = New-Object Text.UTF8Encoding($false)
$previousInputEncoding = [Console]::InputEncoding
try {
    # .NET Framework creates the stdin writer using Console.InputEncoding.
    [Console]::InputEncoding = New-Object Text.UTF8Encoding($false)
    $process = [Diagnostics.Process]::Start($start)
} finally { [Console]::InputEncoding = $previousInputEncoding }
try {
    $outputTask = $process.StandardOutput.ReadToEndAsync()
    $errorTask = $process.StandardError.ReadToEndAsync()
    foreach ($message in $messages) { $process.StandardInput.WriteLine($message) }
    $process.StandardInput.Close()
    if (-not $process.WaitForExit(15000)) {
        $process.Kill()
        $process.WaitForExit()
        throw 'STDIO test process timed out.'
    }
    Assert ($process.ExitCode -eq 0 -and $errorTask.Result.Length -eq 0) 'actual STDIO process exits successfully'
    $stdout = @($outputTask.Result.TrimEnd() -split '\r?\n')
} finally { $process.Dispose() }
$replies = @($stdout | ForEach-Object { $_ | ConvertFrom-Json })
Assert ($replies.Count -eq 5) 'STDIO emits only the expected JSON replies'
Assert ($replies[0].result.protocolVersion -eq '2025-06-18') "STDIO initialization: $($stdout[0])"
Assert ($replies[1].result.tools.Count -eq 35 -and 'sw_component_details' -in $replies[1].result.tools.name -and 'sw_set_global_variable' -in $replies[1].result.tools.name) 'STDIO exposes all 35 schemas'
$featureSchema = $replies[1].result.tools | Where-Object { $_.name -eq 'sw_set_feature_dimensions' }
Assert ('Extrusion' -in $featureSchema.inputSchema.properties.expected_feature_type.enum) 'STDIO schema exposes actual SOLIDWORKS Extrusion type'
Assert ('ProfileFeature' -notin $featureSchema.inputSchema.properties.expected_feature_type.enum) 'STDIO schema still forbids sketch editing'
Assert ($null -ne $replies[2].error -and $replies[3].id -eq 3 -and $null -ne $replies[3].result) 'STDIO recovers after malformed JSON'
Assert ($replies[4].id -eq 4 -and $null -ne $replies[4].error) 'STDIO rejects missing instance_id before calling COM'
Write-Host "PASS: $script:passed assembly-read, dependency and STDIO regression assertions. No live COM calls."
