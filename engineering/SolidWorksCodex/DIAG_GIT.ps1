$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$reportPath = Join-Path $root '_claude_diag_git_report.txt'
if (Test-Path -LiteralPath $reportPath) { Remove-Item -LiteralPath $reportPath -Force }
function Log($text) { Add-Content -LiteralPath $reportPath -Value $text -Encoding UTF8 }

Set-Location -LiteralPath $root
Log ("TIMESTAMP: " + (Get-Date -Format 'o'))
Log ("CWD: " + (Get-Location))
Log ''
Log '=== git status ==='
Log ((git status 2>&1) -join "`n")
Log ''
Log '=== git log --oneline -20 (all branches) ==='
Log ((git log --oneline --all -20 2>&1) -join "`n")
Log ''
Log '=== git branch -a ==='
Log ((git branch -a 2>&1) -join "`n")
Log ''
Log '=== git diff --stat HEAD ==='
Log ((git diff --stat HEAD 2>&1) -join "`n")
Log ''
Log '=== git stash list ==='
Log ((git stash list 2>&1) -join "`n")
Log ''
Log '=== git reflog -20 ==='
Log ((git reflog -20 2>&1) -join "`n")
Log ''
Log '=== ls src ==='
Log ((Get-ChildItem -LiteralPath (Join-Path $root 'src') | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize | Out-String))
Add-Content -LiteralPath $reportPath -Value 'DONE' -Encoding UTF8
