# claude-skills/setup.ps1
# Installs all Claude Code skills globally on Windows
# Usage: ./setup.ps1

$skillsSource = Join-Path $PSScriptRoot ".claude\skills"
$skillsDest = Join-Path $HOME ".claude\skills"

Write-Host "Claude Skills Installer" -ForegroundColor Cyan
Write-Host "=======================" -ForegroundColor Cyan
Write-Host "Source: $skillsSource"
Write-Host "Destination: $skillsDest"
Write-Host ""

if (-not (Test-Path $skillsDest)) {
    New-Item -ItemType Directory -Path $skillsDest -Force | Out-Null
    Write-Host "Created $skillsDest" -ForegroundColor Green
}

$skills = Get-ChildItem -Path $skillsSource -Directory
$count = 0

foreach ($skill in $skills) {
    $destSkill = Join-Path $skillsDest $skill.Name
    if (Test-Path $destSkill) {
        Write-Host "Updating: $($skill.Name)" -ForegroundColor Yellow
        Remove-Item -Path $destSkill -Recurse -Force
    } else {
        Write-Host "Installing: $($skill.Name)" -ForegroundColor Green
    }
    Copy-Item -Path $skill.FullName -Destination $destSkill -Recurse
    $count++
}

Write-Host ""
Write-Host "$count skills installed to $skillsDest" -ForegroundColor Green
Write-Host "Claude Code will pick them up automatically on next session." -ForegroundColor Cyan