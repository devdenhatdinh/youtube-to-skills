# install.ps1 - one-command installer for youtube-to-skill on Windows.
#
#   irm https://raw.githubusercontent.com/devdenhatdinh/youtube-to-skills/main/install.ps1 | iex
#
# Or from a clone:  powershell -ExecutionPolicy Bypass -File install.ps1 [-NoFfmpeg] [-SkipDeps] [-SkillsDir DIR]
#
# Installs yt-dlp (+ ffmpeg for the optional visual pass) with winget, clones or
# updates the skill into ~/.claude/skills/youtube-to-skill, then runs the
# environment checks. Safe to re-run: it updates instead of reinstalling.
# Messages are ASCII on purpose: Windows PowerShell 5.1 misreads non-BOM UTF-8.

param(
    [switch]$NoFfmpeg,
    [switch]$SkipDeps,
    [string]$SkillsDir = (Join-Path $env:USERPROFILE ".claude\skills")
)

$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/devdenhatdinh/youtube-to-skills"
$SkillName = "youtube-to-skill"
$Target = Join-Path $SkillsDir $SkillName

function Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "WARNING: $msg" -ForegroundColor Yellow }
# throw, not exit: under 'irm | iex' exit would close the user's PowerShell window.
function Fail($msg) { throw "ERROR: $msg" }

function Refresh-Path {
    # winget updates the registry PATH, not this session's; reload it.
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Has($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

function Winget-Install($id, $cmd) {
    if (Has $cmd) { Write-Host "    $cmd already installed"; return }
    if (-not (Has "winget")) { Fail "winget not found. Install '$id' manually, then re-run." }
    Write-Host "    installing $id ..."
    winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements | Out-Null
    Refresh-Path
    if (-not (Has $cmd)) {
        Warn "$cmd installed but not on PATH yet; open a new terminal / restart Claude Code."
    }
}

function Find-Python {
    # The WindowsApps 'python3'/'python' stubs open the Store instead of running.
    $candidates = @(
        @{ Exe = "py"; Args = @("-3") },
        @{ Exe = "python"; Args = @() },
        @{ Exe = "python3"; Args = @() }
    )
    foreach ($c in $candidates) {
        if (-not (Has $c.Exe)) { continue }
        try {
            $out = & $c.Exe @($c.Args + "--version") 2>&1
            if ($LASTEXITCODE -eq 0 -and "$out" -match "Python 3\.(\d+)" -and [int]$Matches[1] -ge 8) {
                return $c
            }
        } catch { }
    }
    return $null
}

# 1. Dependencies
if ($SkipDeps) {
    Step "Skipping dependency install (-SkipDeps)"
} else {
    Step "Installing dependencies"
    Winget-Install "Git.Git" "git"
    if (-not (Find-Python)) { Winget-Install "Python.Python.3.12" "py" }
    Winget-Install "yt-dlp.yt-dlp" "yt-dlp"
    if (-not $NoFfmpeg) { Winget-Install "Gyan.FFmpeg" "ffmpeg" }
}

# 2. Skill files
Step "Installing skill into $Target"
if (-not (Has "git")) { Fail "git not found (install Git, then re-run)." }
New-Item -ItemType Directory -Force -Path $SkillsDir | Out-Null
if (Test-Path (Join-Path $Target ".git")) {
    git -C $Target pull --ff-only --quiet
    if ($LASTEXITCODE -ne 0) { Fail "could not update $Target (local changes?). Fix or delete it, then re-run." }
    Write-Host "    updated existing install"
} elseif (Test-Path $Target) {
    Fail "$Target exists but is not a git clone. Move it away, then re-run."
} else {
    git clone --quiet $RepoUrl $Target
    if ($LASTEXITCODE -ne 0) { Fail "git clone failed." }
    Write-Host "    cloned"
}

# 3. Verify
Step "Checking environment"
$py = Find-Python
if (-not $py) { Fail "Python 3.8+ not found. Install it (winget install Python.Python.3.12), then re-run." }
& $py.Exe @($py.Args + (Join-Path $Target "scripts\fetch_transcript.py") + "--check")
$ok = ($LASTEXITCODE -eq 0)
if (-not $NoFfmpeg) { & $py.Exe @($py.Args + (Join-Path $Target "scripts\extract_frames.py") + "--check") }

Write-Host ""
if ($ok) {
    Write-Host "DONE. Restart Claude Code, then try: 'tom tat video nay <youtube-url>'" -ForegroundColor Green
} else {
    Warn "Installed, but yt-dlp is not reachable yet. Restart the terminal / Claude Code and run --check again."
}
