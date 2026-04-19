param(
    [string]$RepoPath = ".",
    [switch]$VerboseCheck
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host "[git-unlock] $msg"
}

try {
    $repo = (Resolve-Path -LiteralPath $RepoPath).Path
} catch {
    Write-Error "Repo path does not exist: $RepoPath"
    exit 1
}

$gitDir = Join-Path $repo ".git"
if (-not (Test-Path -LiteralPath $gitDir)) {
    Write-Error "Cannot find .git directory: $gitDir"
    exit 1
}

Write-Step "Repo: $repo"
Write-Step "Step 1/4: stop stale git processes"
Get-Process git -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Step "Step 2/4: remove lock files under .git"
$lockFiles = @()
$indexLock = Join-Path $gitDir "index.lock"
if (Test-Path -LiteralPath $indexLock) {
    $lockFiles += $indexLock
}

Get-ChildItem -LiteralPath $gitDir -Recurse -File -Filter "*.lock" -ErrorAction SilentlyContinue |
    ForEach-Object {
        if ($_.FullName -notin $lockFiles) {
            $lockFiles += $_.FullName
        }
    }

foreach ($f in $lockFiles) {
    try {
        Remove-Item -LiteralPath $f -Force
        Write-Step "Removed: $f"
    } catch {
        Write-Warning "Failed to remove: $f | $($_.Exception.Message)"
    }
}

Write-Step "Step 3/4: verify .git is writable"
$probe = Join-Path $gitDir "__unlock_probe.tmp"
try {
    "ok" | Set-Content -LiteralPath $probe -Encoding ascii
    Remove-Item -LiteralPath $probe -Force
    Write-Step ".git write check passed"
} catch {
    Write-Error ".git is not writable. This is ACL/permission problem, not stale lock problem. Details: $($_.Exception.Message)"
    exit 2
}

Write-Step "Step 4/4: verify git command"
Push-Location $repo
try {
    git status -sb | Out-Host
} finally {
    Pop-Location
}

if ($VerboseCheck) {
    Write-Step "Extra: current git process list"
    Get-Process git -ErrorAction SilentlyContinue | Format-Table -AutoSize | Out-Host
}

Write-Step "Done"
exit 0
