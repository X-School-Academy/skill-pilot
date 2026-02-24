# Install WSL on modern Windows (Windows 10 build 19041+ / Windows 11).

[CmdletBinding()]
param(
    [string]$Distribution = "Ubuntu-22.04",
    [switch]$NoRestartPrompt
)

$ErrorActionPreference = "Stop"

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-WindowsBuild {
    try {
        $cv = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion"
        return [int]$cv.CurrentBuildNumber
    }
    catch {
        return [int][System.Environment]::OSVersion.Version.Build
    }
}

function Resolve-DistributionName {
    param([string]$InputName)

    if ([string]::IsNullOrWhiteSpace($InputName)) {
        return "Ubuntu-22.04"
    }

    $trimmed = $InputName.Trim()
    $key = $trimmed.ToLowerInvariant()

    $aliasMap = @{
        "ubuntu" = "Ubuntu-22.04"
        "ubuntu-22.04" = "Ubuntu-22.04"
        "ubuntu-24.04" = "Ubuntu-24.04"
        "ubuntu-20.04" = "Ubuntu-20.04"
        "debian" = "Debian"
        "kali" = "kali-linux"
        "kali-linux" = "kali-linux"
        "opensuse" = "openSUSE-Tumbleweed"
        "opensuse-tumbleweed" = "openSUSE-Tumbleweed"
    }

    if ($aliasMap.ContainsKey($key)) {
        return $aliasMap[$key]
    }

    return $trimmed
}

function Get-OnlineDistributions {
    try {
        $lines = & wsl --list --online 2>$null
    }
    catch {
        return @()
    }

    $names = New-Object System.Collections.Generic.List[string]

    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        if ($line -match '^\s*(NAME|The following|Install using|For more information)') {
            continue
        }

        if ($line -match '^\s*([A-Za-z0-9\.\-]+)\s+') {
            $name = $matches[1]
            if (-not $names.Contains($name)) {
                [void]$names.Add($name)
            }
        }
    }

    return $names.ToArray()
}

function Validate-Distribution {
    param([string]$ResolvedDistribution)

    $available = Get-OnlineDistributions
    if ($available.Count -eq 0) {
        return @{
            valid = $true
            canonical = $ResolvedDistribution
            available = @()
            reason = "Could not query online distribution list; skipping strict validation."
        }
    }

    $lookup = @{}
    foreach ($entry in $available) {
        $lookup[$entry.ToLowerInvariant()] = $entry
    }

    $key = $ResolvedDistribution.ToLowerInvariant()
    if ($lookup.ContainsKey($key)) {
        return @{
            valid = $true
            canonical = $lookup[$key]
            available = $available
            reason = "Distribution is available."
        }
    }

    return @{
        valid = $false
        canonical = $ResolvedDistribution
        available = $available
        reason = "Requested distribution is not listed by 'wsl --list --online'."
    }
}

function Write-Summary {
    param(
        [string]$Status,
        [string]$Message,
        [bool]$NeedsRestart,
        [bool]$DistributionInstalled,
        [string]$RequestedDistribution,
        [string]$DistributionName,
        [int]$Build,
        [string[]]$AvailableSuggestions = @()
    )

    $payload = [ordered]@{
        status = $Status
        message = $Message
        build = $Build
        requestedDistribution = $RequestedDistribution
        distribution = $DistributionName
        distributionInstalled = $DistributionInstalled
        needsRestart = $NeedsRestart
        availableSuggestions = $AvailableSuggestions
    }

    Write-Host "\nJSON output:" -ForegroundColor Cyan
    $payload | ConvertTo-Json -Depth 3
}

Write-Host "Starting modern WSL installation..." -ForegroundColor Cyan

if (-not (Test-IsAdministrator)) {
    Write-Host "PowerShell must be run as Administrator." -ForegroundColor Red
    $build = Get-WindowsBuild
    Write-Summary -Status "failed" -Message "Not running as Administrator" -NeedsRestart $false -DistributionInstalled $false -RequestedDistribution $Distribution -DistributionName $Distribution -Build $build
    exit 1
}

$build = Get-WindowsBuild
if ($build -lt 19041) {
    Write-Host "Windows build $build does not support the modern install path." -ForegroundColor Red
    Write-Host "Use scripts/install-wsl-manual.ps1 for legacy setup." -ForegroundColor Yellow
    Write-Summary -Status "failed" -Message "Unsupported build for modern path" -NeedsRestart $false -DistributionInstalled $false -RequestedDistribution $Distribution -DistributionName $Distribution -Build $build
    exit 1
}

if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
    Write-Host "wsl command is not available on this system." -ForegroundColor Red
    Write-Summary -Status "failed" -Message "wsl command not found" -NeedsRestart $false -DistributionInstalled $false -RequestedDistribution $Distribution -DistributionName $Distribution -Build $build
    exit 1
}

$requestedDistribution = $Distribution
$distribution = Resolve-DistributionName -InputName $Distribution
if ($distribution -ne $requestedDistribution) {
    Write-Host "Normalized distribution '$requestedDistribution' -> '$distribution'." -ForegroundColor Yellow
}

$distributionCheck = Validate-Distribution -ResolvedDistribution $distribution
if (-not $distributionCheck.valid) {
    $suggestions = @($distributionCheck.available | Select-Object -First 8)
    Write-Host "Distribution '$distribution' is not available via WSL online catalog." -ForegroundColor Red
    if ($suggestions.Count -gt 0) {
        Write-Host "Try one of: $($suggestions -join ', ')" -ForegroundColor Yellow
    }
    Write-Summary -Status "failed" -Message $distributionCheck.reason -NeedsRestart $false -DistributionInstalled $false -RequestedDistribution $requestedDistribution -DistributionName $distribution -Build $build -AvailableSuggestions $suggestions
    exit 1
}

$distribution = $distributionCheck.canonical

$installedDistros = @()
try {
    $installedDistros = wsl --list --quiet 2>$null |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ }
}
catch {
    $installedDistros = @()
}

$installedLookup = @{}
foreach ($entry in $installedDistros) {
    $installedLookup[$entry.ToLowerInvariant()] = $true
}

$distroAlreadyInstalled = $installedLookup.ContainsKey($distribution.ToLowerInvariant())
$installAttempted = $false

if ($distroAlreadyInstalled) {
    Write-Host "Distribution '$distribution' is already installed. Skipping install command." -ForegroundColor Yellow
}
else {
    Write-Host "Installing WSL and distribution '$distribution'..." -ForegroundColor Yellow
    $installAttempted = $true
    try {
        & wsl --install -d $distribution
        if ($LASTEXITCODE -ne 0) {
            throw "wsl --install exited with code $LASTEXITCODE"
        }
    }
    catch {
        Write-Host "Installation failed: $_" -ForegroundColor Red
        Write-Summary -Status "failed" -Message "wsl --install failed" -NeedsRestart $false -DistributionInstalled $false -RequestedDistribution $requestedDistribution -DistributionName $distribution -Build $build
        exit 1
    }
}

try {
    & wsl --set-default-version 2 | Out-Null
}
catch {
    Write-Host "Could not set default WSL version to 2 automatically. Continue manually if needed." -ForegroundColor Yellow
}

$needsRestart = $installAttempted
$message = if ($installAttempted) { "Installation command completed" } else { "Distribution already installed" }

Write-Host "WSL modern path completed." -ForegroundColor Green
if ($needsRestart) {
    Write-Host "A Windows restart is recommended before first use." -ForegroundColor Yellow
}

Write-Summary -Status "ok" -Message $message -NeedsRestart $needsRestart -DistributionInstalled $true -RequestedDistribution $requestedDistribution -DistributionName $distribution -Build $build

if (-not $NoRestartPrompt -and $needsRestart) {
    $choice = Read-Host "Restart now? (Y/N)"
    if ($choice -match '^[Yy]$') {
        Write-Host "Restarting computer..." -ForegroundColor Cyan
        Restart-Computer
    }
    else {
        Write-Host "Restart skipped. Restart manually before first WSL launch." -ForegroundColor Yellow
    }
}
