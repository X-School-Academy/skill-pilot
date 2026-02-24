# Validate WSL installation and basic runtime functionality.

[CmdletBinding()]
param(
    [switch]$Strict
)

$ErrorActionPreference = "Stop"

function Add-CheckResult {
    param(
        [System.Collections.IDictionary]$Container,
        [string]$Name,
        [bool]$Passed,
        [string]$Details,
        [bool]$Required = $true
    )

    $Container[$Name] = [ordered]@{
        passed = $Passed
        details = $Details
        required = $Required
    }
}

function Invoke-WslCommand {
    param([string]$Command)

    try {
        & wsl -e sh -lc $Command 2>$null
        return [ordered]@{
            exitCode = $LASTEXITCODE
            ok = ($LASTEXITCODE -eq 0)
        }
    }
    catch {
        return [ordered]@{
            exitCode = 1
            ok = $false
        }
    }
}

Write-Host "Running WSL validation checks..." -ForegroundColor Cyan
Write-Host ("Strict mode: {0}" -f $Strict.IsPresent) -ForegroundColor Yellow

$checks = [ordered]@{}

if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
    Add-CheckResult -Container $checks -Name "wsl_command" -Passed $false -Details "wsl command is not available" -Required $true
    $summary = [ordered]@{
        status = "failed"
        strictMode = $Strict.IsPresent
        checks = $checks
        allPassed = $false
        failedChecks = @("wsl_command")
    }

    Write-Host "\nJSON output:" -ForegroundColor Cyan
    $summary | ConvertTo-Json -Depth 5
    exit 1
}

Add-CheckResult -Container $checks -Name "wsl_command" -Passed $true -Details "wsl command is available" -Required $true

$distros = @()
try {
    $distros = wsl --list --quiet 2>$null |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ }
}
catch {
    $distros = @()
}

$distroInstalled = $distros.Count -gt 0
if ($distroInstalled) {
    Add-CheckResult -Container $checks -Name "distribution_installed" -Passed $true -Details ("Installed distributions: " + ($distros -join ", ")) -Required $true
}
else {
    Add-CheckResult -Container $checks -Name "distribution_installed" -Passed $false -Details "No Linux distribution detected" -Required $true
}

$defaultVersion2 = $false
try {
    $statusOutput = wsl --status 2>$null
    $defaultVersion2 = [bool]($statusOutput -match 'Default Version:\s*2')
}
catch {
    $defaultVersion2 = $false
}
Add-CheckResult -Container $checks -Name "default_version_2" -Passed $defaultVersion2 -Details (if ($defaultVersion2) { "Default WSL version is 2" } else { "Could not confirm default version 2" }) -Required $false

$hasWsl2Distro = $false
if ($distroInstalled) {
    try {
        $verbose = wsl --list --verbose 2>$null
        foreach ($line in $verbose) {
            if ($line -match '^\s*\*?\s*([^\s]+)\s+\S+\s+(\d+)\s*$') {
                $version = [int]$matches[2]
                if ($version -eq 2) {
                    $hasWsl2Distro = $true
                    break
                }
            }
        }
    }
    catch {
        $hasWsl2Distro = $false
    }
}
Add-CheckResult -Container $checks -Name "distribution_version_2" -Passed $hasWsl2Distro -Details (if ($hasWsl2Distro) { "At least one distribution is on WSL 2" } else { "Could not confirm a WSL 2 distribution" }) -Required $true

$commandExecution = $false
$aptAvailable = $false
$networkAccess = $false
$windowsDriveAccess = $false
$writeReadTmp = $false

if ($distroInstalled) {
    $echoResult = Invoke-WslCommand -Command "echo wsl-ok >/dev/null"
    $commandExecution = $echoResult.ok
    Add-CheckResult -Container $checks -Name "command_execution" -Passed $commandExecution -Details (if ($commandExecution) { "Able to run shell command in WSL" } else { "Failed to execute shell command in WSL" }) -Required $true

    $aptResult = Invoke-WslCommand -Command "command -v apt >/dev/null 2>&1"
    $aptAvailable = $aptResult.ok
    Add-CheckResult -Container $checks -Name "apt_available" -Passed $aptAvailable -Details (if ($aptAvailable) { "apt command is available" } else { "apt command not found in selected distro" }) -Required $true

    $pingIp = Invoke-WslCommand -Command "ping -c 1 1.1.1.1 >/dev/null 2>&1"
    $pingDns = Invoke-WslCommand -Command "ping -c 1 google.com >/dev/null 2>&1"
    $networkAccess = ($pingIp.ok -or $pingDns.ok)
    $networkDetails = if ($networkAccess) {
        if ($pingIp.ok -and $pingDns.ok) { "Both IP and DNS network checks succeeded" }
        elseif ($pingIp.ok) { "IP network check succeeded" }
        else { "DNS network check succeeded" }
    }
    else {
        "Both IP and DNS network checks failed"
    }
    Add-CheckResult -Container $checks -Name "network_access" -Passed $networkAccess -Details $networkDetails -Required $false

    $driveResult = Invoke-WslCommand -Command "test -d /mnt/c/Windows"
    $windowsDriveAccess = $driveResult.ok
    Add-CheckResult -Container $checks -Name "windows_drive_access" -Passed $windowsDriveAccess -Details (if ($windowsDriveAccess) { "/mnt/c is accessible" } else { "Could not access /mnt/c" }) -Required $true

    $tmpResult = Invoke-WslCommand -Command 'tmp="$(mktemp)"; echo ok > "$tmp"; test "$(cat "$tmp")" = "ok"; rm -f "$tmp"'
    $writeReadTmp = $tmpResult.ok
    Add-CheckResult -Container $checks -Name "write_read_tmp" -Passed $writeReadTmp -Details (if ($writeReadTmp) { "Can write and read temporary files inside WSL" } else { "Failed temporary file read/write test inside WSL" }) -Required $true
}
else {
    Add-CheckResult -Container $checks -Name "command_execution" -Passed $false -Details "Skipped because no distribution is installed" -Required $true
    Add-CheckResult -Container $checks -Name "apt_available" -Passed $false -Details "Skipped because no distribution is installed" -Required $true
    Add-CheckResult -Container $checks -Name "network_access" -Passed $false -Details "Skipped because no distribution is installed" -Required $false
    Add-CheckResult -Container $checks -Name "windows_drive_access" -Passed $false -Details "Skipped because no distribution is installed" -Required $true
    Add-CheckResult -Container $checks -Name "write_read_tmp" -Passed $false -Details "Skipped because no distribution is installed" -Required $true
}

$allPassed = $true
$failedChecks = New-Object System.Collections.Generic.List[string]
foreach ($entry in $checks.GetEnumerator()) {
    $failed = -not $entry.Value.passed
    $shouldCountFailure = if ($Strict.IsPresent) { $failed } else { ($failed -and $entry.Value.required) }
    if ($shouldCountFailure) {
        [void]$failedChecks.Add($entry.Key)
        $allPassed = $false
    }
}

if ($allPassed) {
    Write-Host "All validation checks passed." -ForegroundColor Green
}
else {
    Write-Host "One or more validation checks failed." -ForegroundColor Yellow
}

$summary = [ordered]@{
    status = if ($allPassed) { "ok" } else { "failed" }
    strictMode = $Strict.IsPresent
    checks = $checks
    allPassed = $allPassed
    failedChecks = $failedChecks
}

Write-Host "\nJSON output:" -ForegroundColor Cyan
$summary | ConvertTo-Json -Depth 5

if (-not $allPassed) {
    exit 1
}
