$ErrorActionPreference = 'Stop'
$wordApp = $null
$wordDoc = $null
try {
    $wordApp = New-Object -ComObject Word.Application
    $wordApp.Visible = $false
    $wordApp.DisplayAlerts = 0
    $rootPath = 'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2'
    $inputDoc = Join-Path $rootPath 'outputs\Ленточный_транспортер\01_Техническое_задание\ЛТ500_Паспорт_концепции_R00.docx'
    $pdfFile = Join-Path $rootPath 'work\docx_qa\passport.pdf'
    New-Item -ItemType Directory -Path (Split-Path $pdfFile) -Force | Out-Null
    $wordDoc = $wordApp.Documents.Open($inputDoc, $false, $true)
    $wordDoc.ExportAsFixedFormat($pdfFile, 17)
    Write-Output ('Pages: ' + $wordDoc.ComputeStatistics(2))
    Write-Output $pdfFile
} finally {
    if ($null -ne $wordDoc) { $wordDoc.Close(0) }
    if ($null -ne $wordApp) { $wordApp.Quit() }
}

