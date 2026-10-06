function Get-DependencyPathKey([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or
        ($Path -notmatch '^[A-Za-z]:[\\/]' -and $Path -notmatch '^[\\/]{2}[^\\/]+[\\/][^\\/]+')) {
        throw "Dependency path must be fully qualified: $Path"
    }
    return [IO.Path]::GetFullPath($Path).ToLowerInvariant()
}

function Get-DependencyPaths($DependencyResult) {
    if ($null -eq $DependencyResult -or $null -eq $DependencyResult.data -or
        $DependencyResult.data.api_call_status -ne 'OK' -or $null -eq $DependencyResult.data.dependencies) {
        throw 'Cannot build dependency edges from an unconfirmed API result.'
    }
    # GetDocumentDependencies2(..., AddReadOnlyInfo=false) returns name/path pairs.
    $entries = @($DependencyResult.data.dependencies)
    if ($entries.Count % 2 -ne 0) { throw 'Incomplete dependency name/path pair.' }
    $paths = New-Object 'System.Collections.Generic.HashSet[string]'
    for ($i = 1; $i -lt $entries.Count; $i += 2) {
        [void]$paths.Add((Get-DependencyPathKey ([string]$entries[$i])))
    }
    return ,$paths
}

function Get-ReachableDependencyPaths([hashtable]$DependenciesByPath, [string]$RootPath) {
    $rootKey = Get-DependencyPathKey $RootPath
    $visited = New-Object 'System.Collections.Generic.HashSet[string]'
    [void]$visited.Add($rootKey)
    $queue = New-Object 'System.Collections.Generic.Queue[string]'
    $queue.Enqueue($rootKey)
    while ($queue.Count -gt 0) {
        $current = $queue.Dequeue()
        if (-not $DependenciesByPath.ContainsKey($current)) { continue }
        foreach ($dependency in $DependenciesByPath[$current]) {
            if ($DependenciesByPath.ContainsKey($dependency) -and $visited.Add($dependency)) {
                $queue.Enqueue($dependency)
            }
        }
    }
    return ,$visited
}
