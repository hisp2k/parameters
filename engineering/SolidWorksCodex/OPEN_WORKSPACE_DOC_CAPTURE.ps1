$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $root 'SolidWorksLocal.exe'
$reportPath = Join-Path $root '_claude_open_workspace_doc_report.txt'
if (Test-Path -LiteralPath $reportPath) { Remove-Item -LiteralPath $reportPath -Force }
function Log($text) { Add-Content -LiteralPath $reportPath -Value $text -Encoding UTF8 }

# Re-opens one of our own previously-created, harmless AI-generated test parts
# (from the control test) purely so SOLIDWORKS has an active document again --
# the prior real-PDF test run's document was closed by the connector's own
# failure-cleanup path (CloseDoc when !saved), which left zero documents open
# and made the next tool call fail with NO_ACTIVE_DOCUMENT. This does not
# modify, save, or edit anything -- it only opens an existing local file.
$args = [ordered]@{ file_path = 'C:\Users\root\AppData\Local\SolidWorksCodex\Workspace\AI_PROFILE_PART_20260913_070832_0023b818.SLDPRT' }

try {
    Log 'OPEN WORKSPACE DOC: re-opening an existing AI-generated test part so SOLIDWORKS has an active document.'
    $json = $args | ConvertTo-Json -Depth 5 -Compress
    Log ("REQUEST JSON: " + $json)
    Log ''
    $payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
    $raw = $null
    try { $raw = (& $exe --worker sw_open_local_file $payload 2>&1 | ForEach-Object { $_.ToString() }) -join "`n" }
    catch { $raw = "EXCEPTION DURING WORKER CALL: $_" }
    Log 'RAW RESPONSE:'
    Log $raw
}
catch {
    Log ("UNHANDLED EXCEPTION: " + $_.ToString())
}
Add-Content -LiteralPath $reportPath -Value 'DONE' -Encoding UTF8
