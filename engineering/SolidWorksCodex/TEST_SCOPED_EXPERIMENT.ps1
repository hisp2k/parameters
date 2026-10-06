param([string]$ConnectorPath = (Join-Path $PSScriptRoot 'SolidWorksLocal.exe'))
$ErrorActionPreference='Stop'
$passed=0
function Assert($ok,[string]$name) { if(-not $ok){throw "FAIL: $name"};$script:passed++ }
function Hash([string]$path) { $sha=[Security.Cryptography.SHA256]::Create();try{[BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($path)))}finally{$sha.Dispose()} }
function Code([scriptblock]$action) {try{& $action|Out-Null;'NO_FAULT'}catch{$e=$_.Exception;while($e.InnerException){$e=$e.InnerException};$f=$e.GetType().GetField('Code',[Reflection.BindingFlags]'Instance,NonPublic');if($f){$f.GetValue($e)}else{$e.GetType().Name}}}
Add-Type -Path (Join-Path $PSScriptRoot 'tests\AssemblyReadFixtures.cs')
$a=[Reflection.Assembly]::LoadFrom((Resolve-Path $ConnectorPath).Path)
$t=$a.GetType('SolidWorksLocal.SolidWorksReader',$true)
$flags=[Reflection.BindingFlags]'Instance,NonPublic'
$fixture=[SolidWorks.Interop.sldworks.IModelDoc2].Assembly
$dir=Join-Path ([IO.Path]::GetTempPath()) ('sw_scoped_'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $dir|Out-Null
$file=Join-Path $dir 'part.SLDPRT'
New-Item -ItemType File -Path $file|Out-Null
function New-Fixture {
 $doc=New-Object SolidWorks.Interop.sldworks.IPartDoc
 $doc.PathName=$file;$doc.ReadOnly=$false
 $app=New-Object SolidWorks.Interop.sldworks.ISldWorks
 $app.IActiveDoc2=$doc;$app.AlreadyOpenDocument=$doc;$app.Documents=@($doc)
 $r=[Activator]::CreateInstance($t,$true)
 foreach($entry in @{interop=$fixture;swconst=$fixture;app=$app}.GetEnumerator()){$t.GetField($entry.Key,$flags).SetValue($r,$entry.Value)}
 @{Reader=$r;Doc=$doc;App=$app}
}
function Invoke($f,[string]$method,[object[]]$arguments=@()) {
 for($i=0;$i -lt $arguments.Count;$i++){if($null -ne $arguments[$i]){$arguments[$i]=$arguments[$i].PSObject.BaseObject}}
 return ,($t.GetMethod($method,$flags).Invoke($f.Reader,$arguments))
}
try {
 $f=New-Fixture
 Assert ((Code {Invoke $f TestFile @($dir,(Join-Path $dir '..\outside.SLDPRT'))}) -eq 'TEST_SCOPE_ESCAPE') 'outside path blocked before touching file'
 $f.App.FileDependencyCount=1
 Assert ((Code {Invoke $f TestClosure @($dir,$file)}) -eq 'TEST_DEPENDENCIES_UNKNOWN') 'null dependency array does not hide nonzero count'
 $f.App.FileDependencies=@('outside','C:\Outside\part.SLDPRT')
 Assert ((Code {Invoke $f TestClosure @($dir,$file)}) -eq 'TEST_SCOPE_ESCAPE') 'dependency closure cannot escape'
 $f.App.FileDependencies=@('broken')
 Assert ((Code {Invoke $f TestClosure @($dir,$file)}) -eq 'TEST_DEPENDENCIES_UNKNOWN') 'odd dependency list is rejected'
 $f=New-Fixture;$f.Doc.Dirty=$true
 Assert ((Code {Invoke $f TestDocumentCore @($dir,$file,'close')}) -eq 'TEST_DIRTY_CLOSE_BLOCKED') 'dirty document is not discarded'
 Assert ($f.App.CloseCalls -eq 0) 'dirty close never calls CloseDoc'
 $f=New-Fixture;$f.App.KeepDocumentLoaded=$true
 Assert ((Code {Invoke $f TestDocumentCore @($dir,$file,'reopen')}) -eq 'TEST_DOCUMENT_NOT_UNLOADED') 'retained model cannot claim a fresh reopen'
 Assert ($f.App.OpenDocCallCount -eq 0) 'failed unload does not call OpenDoc6'
 $f=New-Fixture
 $other=New-Object SolidWorks.Interop.sldworks.IModelDoc2
 $other.PathName=$file+'.other';$other.Dependencies=@('part',$file)
 $f.App.Documents=@($f.Doc,$other)
 Assert ((Code {Invoke $f TestNoOpenReferrers @($file)}) -eq 'TEST_DOCUMENT_REFERENCED') 'open parent blocks child unload'
 $f=New-Fixture
 $allowed=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
 $protected=Invoke $f TestProtectDocuments @(,$allowed)
 $f.Doc.Dirty=$true
 Assert ((Code {Invoke $f TestVerifyProtected @(,$protected)}) -eq 'TEST_PROTECTED_DOCUMENT_CHANGED') 'unrelated document dirty flag protected'
 $f=New-Fixture
 $mate=New-Object SolidWorks.Interop.sldworks.IFeature
 $mate.Name='Coincident1';$mate.TypeName='MateCoincident';$mate.ErrorCode=7
 $f.Doc.FirstFeature=$mate
 $health=Invoke $f TestHealth @($f.Doc)
 Assert ($health['error_count'] -eq 1 -and $health['mate_count'] -eq 1 -and $health['status'] -eq 'ISSUES') 'mate feature errors are visible'
 $mate.ErrorIsWarning=$true
 $health=Invoke $f TestHealth @($f.Doc)
 Assert ($health['warning_count'] -eq 1 -and $health['status'] -eq 'ISSUES') 'warnings cannot produce a health PASS'
 $mate.ErrorCode=0
 $health=Invoke $f TestHealth @($f.Doc)
 Assert ($health['error_count'] -eq 0 -and $health['warning_count'] -eq 0 -and $health['status'] -eq 'PASS') 'zero feature codes are clean'
 $mate.TypeName='MaterialFolder'
 $health=Invoke $f TestHealth @($f.Doc)
 Assert ($health['mate_count'] -eq 0) 'material folder is not an assembly mate'
 $f=New-Fixture
 $opened=Invoke $f TestDocumentCore @($dir,$file,'open')
 Assert ($opened['fresh_open'] -eq 'REUSED_ALREADY_LOADED_NOT_FRESH' -and $f.App.OpenDocCallCount -eq 0) 'loaded document is activated without fake disk reopen'
 $f.App.ActivateErrors=2
 $opened=Invoke $f TestDocumentCore @($dir,$file,'open')
 Assert ($opened['activation_code'] -eq 2 -and $opened['activation_requires_rebuild']) 'rebuild activation warning is explicit, not clean load'
 Assert ((Code {Invoke $f TestDocumentCore @($dir,$file,'close')}) -eq 'TEST_REBUILD_REQUIRED') 'activation rebuild warning blocks close'
 $f.App.ActivateErrors=1
 Assert ((Code {Invoke $f TestDocumentCore @($dir,$file,'open')}) -eq 'TEST_ACTIVATE_FAILED') 'generic activation error remains blocked'
 $f=New-Fixture;$f.Doc.ReadOnly=$true
 $blocked=Code {Invoke $f TestDocumentCore @($dir,$file,'rebuild_save')}
 Assert ($blocked -ne 'NO_FAULT' -and $f.Doc.RebuildCalls -eq 0 -and $f.Doc.SaveCalls -eq 0) 'read-only experiment cannot rebuild or save'
 $f=New-Fixture;$f.Doc.RebuildSuccess=$false
 Assert ((Code {Invoke $f TestDocumentCore @($dir,$file,'rebuild_save')}) -eq 'TEST_REBUILD_FAILED') 'failed experiment rebuild rejected'
 Assert ($f.Doc.SaveCalls -eq 0) 'failed experiment rebuild never saves'
 $f=New-Fixture
 $feature=New-Object SolidWorks.Interop.sldworks.IFeature
 $feature.ErrorCode=7;$f.Doc.FirstFeature=$feature
 Assert ((Code {Invoke $f TestDocumentCore @($dir,$file,'rebuild_save')}) -eq 'TEST_FEATURE_ERRORS') 'unhealthy experiment feature prevents save'
 Assert ($f.Doc.SaveCalls -eq 0) 'unhealthy experiment never saves'
 $f=New-Fixture
 $saved=Invoke $f TestDocumentCore @($dir,$file,'rebuild_save')
 Assert ($saved['saved'] -and $f.Doc.SaveCalls -eq 1 -and $f.Doc.RebuildCalls -eq 1) 'clean experiment rebuild saves exactly the target once'
 $backup=$saved['backups'][0]['backup']
 Assert ((Test-Path -LiteralPath $backup) -and (Hash $backup) -eq (Hash $file)) 'experiment backup exists and matches source'
 $f=New-Fixture;$f.Doc.DocumentType=2
 Assert ((Code {Invoke $f TestActivate @($file)}) -eq 'TEST_DOCUMENT_TYPE') 'loaded document type must match requested native extension'
} finally {
 # Only files in this uniquely created, flat scratch directory are removed.
 Get-ChildItem -LiteralPath $dir -File|ForEach-Object {Remove-Item -LiteralPath $_.FullName -Force}
 Remove-Item -LiteralPath $dir
}
Write-Host "PASS: $passed scoped experiment assertions. No live COM calls."
