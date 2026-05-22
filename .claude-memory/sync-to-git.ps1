# 메모리 → git 폴더로 복사 (Push 방향)
# 사용법: 프로젝트 루트에서 powershell -ExecutionPolicy Bypass -File .claude-memory\sync-to-git.ps1
# (또는) .\.claude-memory\sync-to-git.ps1

$ErrorActionPreference = "Stop"

$src = Join-Path $env:USERPROFILE ".claude\projects\d--Free-Vue\memory"
$dst = Join-Path $PSScriptRoot ""

if (-not (Test-Path $src)) {
    Write-Host "ERROR: source not found: $src" -ForegroundColor Red
    exit 1
}

Write-Host "Source: $src"
Write-Host "Target: $dst"

# .md 파일만 복사
Get-ChildItem -Path $src -Filter "*.md" | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $dst -Force
    Write-Host "  copied: $($_.Name)"
}

Write-Host ""
Write-Host "[done] Memory synced to git folder." -ForegroundColor Green
Write-Host "Next: git add .claude-memory/ && git commit && git push"
