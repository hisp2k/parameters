$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$messages = @(
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"manual-test","version":"1"}}}',
    '{"jsonrpc":"2.0","method":"notifications/initialized"}',
    '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
)
$messages | & (Join-Path $root 'SolidWorksLocal.exe') --stdio
Write-Host ''
Write-Host 'Expected: JSON replies with id 1 and id 2.'
Read-Host 'Press Enter to close'
