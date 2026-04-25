param(
    [string]$RepoPath = "D:\shop",
    [string]$BranchName = "iter4-main",
    [string]$DenySid = "S-1-5-21-3776489676-511968966-490825447-405851410"
)

$ErrorActionPreference = "Continue"

$gitDir = Join-Path $RepoPath ".git"
$indexLock = Join-Path $gitDir "index.lock"
$branchLock = Join-Path $gitDir "refs\heads\$BranchName.lock"

Write-Host "========================================"
Write-Host "Fix Git Permission"
Write-Host "RepoPath: $RepoPath"
Write-Host "GitDir  : $gitDir"
Write-Host "Branch  : $BranchName"
Write-Host "========================================"

Write-Host ""
Write-Host "[1/5] Stop git processes..."
Get-Process git -ErrorAction SilentlyContinue | Stop-Process -Force

Write-Host ""
Write-Host "[2/5] Remove lock files..."
Remove-Item -LiteralPath $indexLock -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $branchLock -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "[3/5] Take ownership of .git..."
takeown /F $gitDir /R /D Y

Write-Host ""
Write-Host "[4/5] Remove blocking DENY permission..."
icacls $gitDir /remove "*$DenySid" /T /C

Write-Host ""
Write-Host "[5/5] Grant full control to current user, Administrators and SYSTEM..."
$me = whoami
icacls $gitDir /grant:r "${me}:(OI)(CI)F" "BUILTIN\Administrators:(OI)(CI)F" "NT AUTHORITY\SYSTEM:(OI)(CI)F" /T /C

Write-Host ""
Write-Host "========================================"
Write-Host "Verify"
Write-Host "========================================"
icacls $gitDir
if (Test-Path -LiteralPath (Join-Path $gitDir "index")) {
    icacls (Join-Path $gitDir "index")
}
git -C $RepoPath status -sb

Write-Host ""
Write-Host "Done. If DENY still appears, run this script in Administrator PowerShell."
