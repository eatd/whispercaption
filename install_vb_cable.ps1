# VB-Cable Automated Installer Helper
# This script downloads and guides you through VB-Cable installation

param(
    [switch]$SkipDownload
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$downloadUrl = "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack43.zip"
$tempDir = "$env:TEMP\VBCable"
$zipPath = "$tempDir\VBCABLE.zip"
$extractPath = "$tempDir\Extracted"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VB-Cable Installation Helper" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if already installed
# Check for admin rights
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "❌ Please run this script as Administrator." -ForegroundColor Red
    exit 1
}

# Check if Get-PnpDevice is available
if (-not (Get-Command Get-PnpDevice -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Get-PnpDevice cmdlet not found. Please ensure you are running Windows 10/11 and have the PnpDevice module installed." -ForegroundColor Red
    Write-Host "You may need to update PowerShell or install the module manually." -ForegroundColor Yellow
    exit 1
}

$devices = Get-PnpDevice -Class "MEDIA" | Where-Object { $_.FriendlyName -like "*CABLE*" }
if ($devices) {
    Write-Host "✅ VB-Cable appears to be already installed:" -ForegroundColor Green
    $devices | ForEach-Object { Write-Host "   - $($_.FriendlyName)" -ForegroundColor Gray }
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") { exit 0 }
}

if (-not $SkipDownload) {
    # Create temp directory
    if (-not (Test-Path $tempDir)) {
        New-Item -ItemType Directory -Path $tempDir | Out-Null
    }

    Write-Host "📦 Downloading VB-Cable from official site..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing
        Write-Host "✅ Download complete!" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Download failed: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "Manual download: $downloadUrl" -ForegroundColor Cyan
        exit 1
    }

    # Extract
    Write-Host "📂 Extracting files..." -ForegroundColor Yellow
    if (Test-Path $extractPath) {
        Remove-Item $extractPath -Recurse -Force
    }
    Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
    Write-Host "✅ Extraction complete!" -ForegroundColor Green
}
else {
    Write-Host "⏭️ Skipping download (using existing files)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  INSTALLATION INSTRUCTIONS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1️⃣  The installer will now open" -ForegroundColor Yellow
Write-Host "2️⃣  Click 'Install Driver' button" -ForegroundColor Yellow
Write-Host "3️⃣  Click 'Yes' on Windows security prompt" -ForegroundColor Yellow
Write-Host "4️⃣  Wait for 'Installation Complete' message" -ForegroundColor Yellow
Write-Host "5️⃣  REBOOT your computer (required for driver)" -ForegroundColor Red
Write-Host ""

$ready = Read-Host "Press ENTER to open the installer..."
# Find installer executable

# Detect architecture
$arch = if ([Environment]::Is64BitOperatingSystem) { "x64" } else { "x86" }
$installer = Get-ChildItem -Path $extractPath -Filter "VBCABLE_Setup_$arch.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1

# Fallback: search for any VBCABLE_Setup*.exe if the expected one is not found
if (-not $installer) {
    $installer = Get-ChildItem -Path $extractPath -Filter "VBCABLE_Setup*.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($installer) {
        Write-Host "⚠️  Expected installer not found, using fallback: $($installer.Name)" -ForegroundColor Yellow
    }
}

if ($installer) {
    Write-Host "🚀 Launching installer..." -ForegroundColor Green
    Start-Process -FilePath $installer.FullName -Verb RunAs -Wait

    Write-Host "🔄 Rebooting in 3 seconds..." -ForegroundColor Yellow
    Start-Sleep 3
    Restart-Computer -Force
    Write-Host "⚠️  IMPORTANT: You MUST REBOOT for the driver to work!" -ForegroundColor Red
    Write-Host ""

    $reboot = Read-Host "Reboot now? (y/n)"
    if ($reboot -eq "y") {
        Write-Host "🔄 Rebooting in 10 seconds..." -ForegroundColor Yellow
        Start-Sleep 3
        Restart-Computer -Force
    }
}
else {
    Write-Host "❌ Could not find installer executable" -ForegroundColor Red
    Write-Host "Check: $extractPath" -ForegroundColor Gray
    Write-Host "Possible issues: Extraction failed, antivirus removed files, or manual extraction needed." -ForegroundColor Yellow
    Write-Host "Try extracting the ZIP manually and ensure the installer is present, or temporarily disable antivirus." -ForegroundColor Yellow
    exit 1
}
