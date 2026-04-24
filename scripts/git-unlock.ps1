param(
    [string]$RepoPath = (Get-Location).Path,
    [string]$DenySid = "S-1-5-21-3776489676-511968966-490825447-405851410",
    [switch]$SkipAclFix,
    [switch]$SkipKillGit,
    [switch]$DeepAclRepair
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "========================================"
    Write-Host $Message
    Write-Host "========================================"
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Resolve-GitDir {
    param([string]$Path)

    $gitDir = Join-Path $Path ".git"
    if (Test-Path -LiteralPath $gitDir) {
        return (Resolve-Path -LiteralPath $gitDir).Path
    }

    $resolved = git -C $Path rev-parse --git-dir 2>$null
    if ($LASTEXITCODE -eq 0 -and $resolved) {
        if ([System.IO.Path]::IsPathRooted($resolved)) {
            return $resolved
        }
        return (Resolve-Path -LiteralPath (Join-Path $Path $resolved)).Path
    }

    throw "Cannot find .git directory under: $Path"
}

function Remove-GitLocks {
    param([string]$GitDir)

    $locks = Get-ChildItem -LiteralPath $GitDir -Recurse -Force -Filter "*.lock" -ErrorAction SilentlyContinue
    if (-not $locks) {
        Write-Ok "No Git lock files found."
        return
    }

    foreach ($lock in $locks) {
        try {
            Remove-Item -LiteralPath $lock.FullName -Force
            Write-Ok "Removed lock: $($lock.FullName)"
        } catch {
            Write-Warn "Failed to remove lock: $($lock.FullName). $($_.Exception.Message)"
        }
    }
}

function Stop-GitProcesses {
    $gitProcesses = Get-Process -Name git -ErrorAction SilentlyContinue
    if (-not $gitProcesses) {
        Write-Ok "No running git.exe process found."
        return
    }

    foreach ($proc in $gitProcesses) {
        try {
            Stop-Process -Id $proc.Id -Force
            Write-Ok "Stopped git.exe PID=$($proc.Id)"
        } catch {
            Write-Warn "Failed to stop git.exe PID=$($proc.Id). $($_.Exception.Message)"
        }
    }
}

function Repair-GitAcl {
    param(
        [string]$GitDir,
        [string]$DenySid,
        [switch]$DeepAclRepair
    )

    $me = whoami
    Write-Host "Current user: $me"

    if ($DeepAclRepair) {
        Write-Host "Taking ownership of .git metadata..."
        takeown /F $GitDir /R /D Y | Out-Host

        Write-Host "Disabling ACL inheritance on .git metadata..."
        icacls $GitDir /inheritance:r /T /C | Out-Host
    }

    Write-Host "Removing known DENY SID: $DenySid"
    icacls $GitDir /remove:d "*$DenySid" /T /C | Out-Host
    icacls $GitDir /remove:d "$DenySid" /T /C | Out-Host

    Write-Host "Granting full control to current user, Administrators, and SYSTEM"
    icacls $GitDir /grant:r "${me}:(OI)(CI)F" "BUILTIN\Administrators:(OI)(CI)F" "NT AUTHORITY\SYSTEM:(OI)(CI)F" /T /C | Out-Host

    $indexPath = Join-Path $GitDir "index"
    $aclText = (icacls $GitDir) -join "`n"
    if (Test-Path -LiteralPath $indexPath) {
        $aclText += "`n" + ((icacls $indexPath) -join "`n")
    }
    if ($aclText -match "DENY") {
        Write-Warn "DENY entry still exists under $GitDir. Re-run as Administrator with -DeepAclRepair if Git is still blocked."
    } else {
        Write-Ok "No DENY entry found on .git root/index."
    }
}

function Test-GitWritable {
    param([string]$RepoPath)

    git -C $RepoPath status --short | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "git status failed."
    }

    $gitDir = Resolve-GitDir $RepoPath
    $testLock = Join-Path $gitDir "codex-write-test.lock"
    try {
        "test" | Set-Content -LiteralPath $testLock -Encoding ASCII
        Remove-Item -LiteralPath $testLock -Force
        Write-Ok "Git metadata directory is writable."
    } catch {
        throw "Cannot write test lock under .git: $($_.Exception.Message)"
    }
}

try {
    $RepoPath = (Resolve-Path -LiteralPath $RepoPath).Path
    $gitDir = Resolve-GitDir $RepoPath

    Write-Step "Git Unlock Tool"
    Write-Host "Repository: $RepoPath"
    Write-Host "Git dir   : $gitDir"

    if (-not $SkipKillGit) {
        Write-Step "1/4 Stop running git.exe"
        Stop-GitProcesses
    }

    Write-Step "2/4 Remove Git lock files"
    Remove-GitLocks -GitDir $gitDir

    if (-not $SkipAclFix) {
        Write-Step "3/4 Repair .git ACL"
        Repair-GitAcl -GitDir $gitDir -DenySid $DenySid -DeepAclRepair:$DeepAclRepair
    } else {
        Write-Warn "SkipAclFix is enabled. ACL repair skipped."
    }

    Write-Step "4/4 Verify Git availability"
    Test-GitWritable -RepoPath $RepoPath

    Write-Step "Done"
    Write-Ok "Git unlock completed. You can retry git add / commit now."
    exit 0
} catch {
    Write-Fail $_.Exception.Message
    exit 1
}
