# Check Windows compatibility and readiness for WSL installation.

[CmdletBinding()]
param()

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

Write-Host "Checking Windows compatibility for WSL..." -ForegroundColor Cyan

$version = [System.Environment]::OSVersion.Version
$build = Get-WindowsBuild
$major = $version.Major
$minor = $version.Minor

$osName = "Unknown"
$osVersion = "Unknown"
try {
    $osInfo = Get-ComputerInfo | Select-Object OsName, OsVersion
    $osName = $osInfo.OsName
    $osVersion = $osInfo.OsVersion
}
catch {
    $osVersion = $version.ToString()
}

Write-Host ""
Write-Host "Windows Version Information:" -ForegroundColor Yellow
Write-Host "  Name: $osName"
Write-Host "  Version: $osVersion"
Write-Host "  Major: $major"
Write-Host "  Minor: $minor"
Write-Host "  Build: $build"

$compatible = $false
$method = "unsupported"

if ($major -ge 10) {
    if ($build -ge 19041) {
        $compatible = $true
        $method = "modern"
        Write-Host "\nWSL path: modern installation (wsl --install)" -ForegroundColor Green
    }
    elseif ($build -ge 18362) {
        $compatible = $true
        $method = "manual"
        Write-Host "\nWSL path: manual installation (feature enable + kernel update)" -ForegroundColor Yellow
    }
    else {
        Write-Host "\nWSL 2 is not supported on this build. Update Windows first." -ForegroundColor Red
    }
}
else {
    Write-Host "\nWindows 10 or later is required for WSL." -ForegroundColor Red
}

$isAdmin = Test-IsAdministrator
Write-Host "\nAdministrator status:" -ForegroundColor Yellow
if ($isAdmin) {
    Write-Host "  Running as Administrator" -ForegroundColor Green
}
else {
    Write-Host "  Not running as Administrator" -ForegroundColor Yellow
}

$freeGB = 0.0
try {
    $drive = Get-PSDrive -Name C
    $freeGB = [math]::Round(($drive.Free / 1GB), 2)
}
catch {
    $freeGB = 0.0
}

Write-Host "\nDisk space:" -ForegroundColor Yellow
Write-Host "  Free space on C: $freeGB GB"

$ramGB = 0.0
try {
    $ram = Get-CimInstance Win32_ComputerSystem | Select-Object -First 1 -ExpandProperty TotalPhysicalMemory
    $ramGB = [math]::Round(($ram / 1GB), 2)
}
catch {
    $ramGB = 0.0
}

Write-Host "\nRAM:" -ForegroundColor Yellow
Write-Host "  Total RAM: $ramGB GB"

$virtualizationStatus = "unknown"
try {
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $cs = Get-CimInstance Win32_ComputerSystem | Select-Object -First 1

    $firmwareEnabled = $null
    if ($cpu.PSObject.Properties.Name -contains "VirtualizationFirmwareEnabled") {
        $firmwareEnabled = [bool]$cpu.VirtualizationFirmwareEnabled
    }

    $hypervisorPresent = [bool]$cs.HypervisorPresent

    if ($firmwareEnabled -eq $true -or $hypervisorPresent) {
        $virtualizationStatus = "enabled"
    }
    elseif ($firmwareEnabled -eq $false -and -not $hypervisorPresent) {
        $virtualizationStatus = "disabled"
    }
}
catch {
    $virtualizationStatus = "unknown"
}

Write-Host "\nVirtualization:" -ForegroundColor Yellow
Write-Host "  Status: $virtualizationStatus"
if ($virtualizationStatus -eq "disabled") {
    Write-Host "  WSL 2 requires virtualization in BIOS/UEFI." -ForegroundColor Yellow
}

$diskOk = $freeGB -ge 10
$ramOk = $ramGB -ge 4
$virtOk = $virtualizationStatus -ne "disabled"
$readyToInstall = $compatible -and $isAdmin -and $diskOk -and $ramOk -and $virtOk

Write-Host "\n" + ("=" * 50) -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host ("=" * 50) -ForegroundColor Cyan

if ($readyToInstall) {
    Write-Host "System is ready for WSL installation." -ForegroundColor Green
    Write-Host "Recommended method: $method"
}
else {
    Write-Host "Readiness checks failed:" -ForegroundColor Yellow
    if (-not $compatible) { Write-Host "  - Windows build does not support requested WSL path" }
    if (-not $isAdmin) { Write-Host "  - PowerShell must be run as Administrator" }
    if (-not $diskOk) { Write-Host "  - At least 10 GB free disk space is recommended" }
    if (-not $ramOk) { Write-Host "  - At least 4 GB RAM is required" }
    if (-not $virtOk) { Write-Host "  - Virtualization appears disabled" }
}

$summary = [ordered]@{
    compatible = $compatible
    method = $method
    isAdmin = $isAdmin
    build = $build
    osName = $osName
    osVersion = $osVersion
    freeGB = $freeGB
    ramGB = $ramGB
    virtualizationStatus = $virtualizationStatus
    readyToInstall = $readyToInstall
}

Write-Host "\nJSON output:" -ForegroundColor Cyan
$summary | ConvertTo-Json -Depth 4
