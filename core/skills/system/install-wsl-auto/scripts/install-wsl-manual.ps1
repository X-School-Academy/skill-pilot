# Manual WSL setup flow for older Windows 10 builds.
# Phase 1 (default): enable required Windows features and restart.
# Phase 2 (-ContinueAfterRestart): finish WSL 2 defaults and install distribution.

[CmdletBinding()]
param(
    [switch]$ContinueAfterRestart,
    [string]$Distribution = "Ubuntu-22.04",
    [switch]$NoRestartPrompt
)

$ErrorActionPreference = "Stop"

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
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
        [string]$Phase,
        [string]$Status,
        [string]$Message,
        [bool]$NeedsRestart,
        [bool]$KernelUpdateRequired,
        [string]$RequestedDistribution,
        [string]$DistributionName,
        [string]$NextStep,
        [string[]]$AvailableSuggestions = @()
    )

    $payload = [ordered]@{
        phase = $Phase
        status = $Status
        message = $Message
        requestedDistribution = $RequestedDistribution
        distribution = $DistributionName
        needsRestart = $NeedsRestart
        kernelUpdateRequired = $KernelUpdateRequired
        nextStep = $NextStep
        availableSuggestions = $AvailableSuggestions
    }

    Write-Host "\nJSON output:" -ForegroundColor Cyan
    $payload | ConvertTo-Json -Depth 3
}

function Enable-Feature {
    param([string]$FeatureName)

    Write-Host "Enabling feature: $FeatureName" -ForegroundColor Yellow
    & dism.exe /online /enable-feature /featurename:$FeatureName /all /norestart

    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 3010) {
        throw "DISM failed while enabling $FeatureName (exit code $LASTEXITCODE)."
    }
}

Write-Host "Starting manual WSL installation path..." -ForegroundColor Cyan

$requestedDistribution = $Distribution
$distribution = Resolve-DistributionName -InputName $Distribution
if ($distribution -ne $requestedDistribution) {
    Write-Host "Normalized distribution '$requestedDistribution' -> '$distribution'." -ForegroundColor Yellow
}

if (-not (Test-IsAdministrator)) {
    Write-Host "PowerShell must be run as Administrator." -ForegroundColor Red
    Write-Summary -Phase "pre-restart" -Status "failed" -Message "Not running as Administrator" -NeedsRestart $false -KernelUpdateRequired $false -RequestedDistribution $requestedDistribution -DistributionName $distribution -NextStep "Reopen PowerShell as Administrator and rerun the script."
    exit 1
}

if (-not $ContinueAfterRestart) {
    try {
        Enable-Feature -FeatureName "Microsoft-Windows-Subsystem-Linux"
        Enable-Feature -FeatureName "VirtualMachinePlatform"
    }
    catch {
        Write-Host "Feature enable failed: $_" -ForegroundColor Red
        Write-Summary -Phase "pre-restart" -Status "failed" -Message "Could not enable required Windows features" -NeedsRestart $false -KernelUpdateRequired $false -RequestedDistribution $requestedDistribution -DistributionName $distribution -NextStep "Resolve DISM errors and rerun the script."
        exit 1
    }

    Write-Host "Required features enabled. Restart is required before continuing." -ForegroundColor Green
    Write-Summary -Phase "pre-restart" -Status "ok" -Message "Features enabled" -NeedsRestart $true -KernelUpdateRequired $false -RequestedDistribution $requestedDistribution -DistributionName $distribution -NextStep "Restart Windows, then run this script with -ContinueAfterRestart."

    if (-not $NoRestartPrompt) {
        $choice = Read-Host "Restart now? (Y/N)"
        if ($choice -match '^[Yy]$') {
            Restart-Computer
        }
        else {
            Write-Host "Restart skipped. You must restart before continuing." -ForegroundColor Yellow
        }
    }

    exit 0
}

if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
    Write-Host "wsl command is not available yet. Confirm Windows has restarted." -ForegroundColor Red
    Write-Summary -Phase "post-restart" -Status "failed" -Message "wsl command not found" -NeedsRestart $false -KernelUpdateRequired $false -RequestedDistribution $requestedDistribution -DistributionName $distribution -NextStep "Restart Windows and rerun this command."
    exit 1
}

$distributionCheck = Validate-Distribution -ResolvedDistribution $distribution
if (-not $distributionCheck.valid) {
    $suggestions = @($distributionCheck.available | Select-Object -First 8)
    Write-Host "Distribution '$distribution' is not available via WSL online catalog." -ForegroundColor Red
    if ($suggestions.Count -gt 0) {
        Write-Host "Try one of: $($suggestions -join ', ')" -ForegroundColor Yellow
    }
    Write-Summary -Phase "post-restart" -Status "failed" -Message $distributionCheck.reason -NeedsRestart $false -KernelUpdateRequired $false -RequestedDistribution $requestedDistribution -DistributionName $distribution -NextStep "Choose a listed distribution and rerun post-restart step." -AvailableSuggestions $suggestions
    exit 1
}

$distribution = $distributionCheck.canonical

$kernelUpdateRequired = $false
$kernelUpdateUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"

try {
    & wsl --set-default-version 2 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $kernelUpdateRequired = $true
    }
}
catch {
    $kernelUpdateRequired = $true
}

if ($kernelUpdateRequired) {
    Write-Host "WSL 2 kernel update appears to be required." -ForegroundColor Yellow
    Write-Host "Download and install: $kernelUpdateUrl"
}

$installedViaCommand = $false
$installError = $null

try {
    & wsl --install -d $distribution
    if ($LASTEXITCODE -eq 0) {
        $installedViaCommand = $true
    }
}
catch {
    $installError = $_
}

if ($installedViaCommand) {
    Write-Host "Distribution install command executed for '$distribution'." -ForegroundColor Green
    Write-Summary -Phase "post-restart" -Status "ok" -Message "Post-restart setup completed" -NeedsRestart $false -KernelUpdateRequired $kernelUpdateRequired -RequestedDistribution $requestedDistribution -DistributionName $distribution -NextStep "Launch $distribution and complete first-run username/password setup."
    exit 0
}

Write-Host "Could not auto-install distribution via command." -ForegroundColor Yellow
if ($installError) {
    Write-Host "Install command error: $installError" -ForegroundColor Yellow
}

Write-Host "Install the distribution manually from Microsoft Store:" -ForegroundColor Yellow
Write-Host "  1. Open Microsoft Store"
Write-Host "  2. Search for $distribution"
Write-Host "  3. Install and launch it once"

Write-Summary -Phase "post-restart" -Status "ok" -Message "Post-restart setup completed with manual distribution install fallback" -NeedsRestart $false -KernelUpdateRequired $kernelUpdateRequired -RequestedDistribution $requestedDistribution -DistributionName $distribution -NextStep "Install distribution from Store, launch it, and finish first-run setup."
