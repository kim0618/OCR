# git 폴더 → 메모리로 복사 (Pull 방향)
# 사용법: 프로젝트 루트에서 powershell -ExecutionPolicy Bypass -File .claude-memory\sync-from-git.ps1
# (또는) .\.claude-memory\sync-from-git.ps1
# git pull 받은 직후 실행할 것.

$ErrorActionPreference = "Stop"

$src = Join-Path $PSScriptRoot ""
$dst = Join-Path $env:USERPROFILE ".claude\projects\d--Free-Vue\memory"

if (-not (Test-Path $dst)) {
    New-Item -ItemType Directory -Path $dst -Force | Out-Null
    Write-Host "Created memory folder: $dst"
}

Write-Host "Source: $src"
Write-Host "Target: $dst"

# .md 파일만 복사 (README.md, *.ps1 같은 거 제외하려면 추가 필터)
Get-ChildItem -Path $src -Filter "*.md" | Where-Object {
    $_.Name -ne "README.md"
} | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $dst -Force
    Write-Host "  copied: $($_.Name)"
}

Write-Host ""
Write-Host "[done] Memory loaded into Claude's memory folder." -ForegroundColor Green
Write-Host "Claude can now use the synced memory in future conversations."
