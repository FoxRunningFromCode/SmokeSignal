<#
PowerShell script to build a Windows executable and optional installer for SmokeSignal.

Usage (from repository root, PowerShell):
  .\tools\build_windows_installer.ps1 [-Clean] [-OneFile]

What it does:
 - Creates a virtualenv under .venv_build
 - Installs dependencies from requirements.txt and pyinstaller
 - Runs PyInstaller to build a Windows executable (one-folder by default)
 - Optionally runs Inno Setup (ISCC) to produce an installer using installer\SmokeSignal.iss

Notes:
 - Requires Python 3.8+ installed and available on PATH.
 - PyQt6 and ReportLab can be tricky with pyinstaller; the script includes common hidden-import hints but you may need to adapt.
 - If you want a single-file exe, pass -OneFile.
#>
param(
    [switch]$Clean,
    [switch]$OneFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Compute repository root (script is in tools/). Use repo root as working directory so relative paths like src\main.py resolve.
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $scriptDir "..") | Select-Object -ExpandProperty Path
Push-Location $root

$venvDir = Join-Path $root ".venv_build"
if ($Clean -and (Test-Path $venvDir)) {
    Write-Host "Removing existing build venv..."
    Remove-Item -Recurse -Force $venvDir
}

if (-not (Test-Path $venvDir)) {
    python -m venv "$venvDir"
}

$activate = Join-Path $venvDir "Scripts\Activate.ps1"
if (-not (Test-Path $activate)) {
    Write-Error "Failed to find virtualenv activation script at $activate"
    exit 1
}

Write-Host "Activating virtualenv..."
. $activate

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

Write-Host "Installing requirements..."
if (Test-Path "requirements.txt") {
    python -m pip install -r requirements.txt
}

Write-Host "Installing pyinstaller..."
python -m pip install pyinstaller

# Common PyInstaller options
$entry = "src\main.py"
$name = "SmokeSignal"
$distpath = Join-Path $root "dist"
$workpath = Join-Path $root "build"
$specpath = $root

# Add data folders (format for --add-data is 'src;src' on Windows)
$addData = @(
    "resources;resources",
    "README.md;." 
)

# Hidden imports heuristics (may need to expand)
$hiddenImports = @(
    "PyQt6",
    "PyQt6.QtGui",
    "reportlab.pdfbase.ttfonts",
    "reportlab.rl_config"
)

$extraArgs = @()
if ($OneFile) { $extraArgs += "--onefile" }
$extraArgs += @("--name", $name, "--distpath", $distpath, "--workpath", $workpath, "--specpath", $specpath, "--noconfirm", "--clean")

foreach ($h in $hiddenImports) { $extraArgs += "--hidden-import"; $extraArgs += $h }
foreach ($d in $addData) { $extraArgs += "--add-data"; $extraArgs += $d }

# Windowed app (no console)
$extraArgs += "--windowed"

# Build
Write-Host "Running PyInstaller..."
pyinstaller $entry $extraArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "PyInstaller build complete. Output: $distpath\$name"

# Optional: build installer using Inno Setup (ISCC)
$iss = Join-Path $root "installer\SmokeSignal.iss"
if (Test-Path $iss) {
    # Look for ISCC.exe on PATH
    $iscc = Get-Command -ErrorAction SilentlyContinue ISCC.exe
    if ($null -ne $iscc) {
        Write-Host "Found Inno Setup compiler: $($iscc.Path). Building installer..."
        & $iscc.Path $iss
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Inno Setup compilation failed with exit code $LASTEXITCODE"
        } else {
            Write-Host "Installer created (check installer output folder)."
        }
    } else {
        Write-Host "Inno Setup compiler (ISCC.exe) not found on PATH. Skipping installer creation."
        Write-Host "You can install Inno Setup and then re-run this script or run: ISCC.exe installer\SmokeSignal.iss"
    }
} else {
    Write-Host "No Inno Setup script found at installer\SmokeSignal.iss. Skipping installer creation."
}

Write-Host "Build script finished."
Pop-Location
