<#
Build script for creating a single-file Windows EXE using PyInstaller.

Usage (PowerShell):
  .\build_exe.ps1

This script will:
- create a virtual environment in `.venv_build` (if missing)
- install build dependencies (`pyinstaller`) into it
- run PyInstaller to build a single-window executable `windwoslh.exe` from `windwoslh.py`

Notes:
- Run this script from the repository root (same folder as `windwoslh.py`).
- You may need to run PowerShell as Administrator to install packages globally; this script installs into the venv only.
#>

Set-StrictMode -Version Latest

$here = Split-Path -Parent $MyInvocation.MyCommand.Definition
Push-Location $here

if (-not (Test-Path .venv_build)) {
    python -m venv .venv_build
}

$venvPython = Join-Path $here ".venv_build\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Error "Cannot find python in .venv_build; ensure Python is installed and available as 'python'."
    Exit 1
}

# Upgrade pip and install pyinstaller
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install pyinstaller

# Build with PyInstaller
# --noconfirm: overwrite dist/build dirs
# --onefile: single EXE
# --windowed: no console window
# You can change --onefile to --onedir for easier debugging
& $venvPython -m PyInstaller --noconfirm --onefile --windowed --name windwoslh windwoslh.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed with exit code $LASTEXITCODE"
    Pop-Location
    Exit $LASTEXITCODE
}

$distExe = Join-Path $here "dist\windwoslh.exe"
if (Test-Path $distExe) {
    Write-Output "Build succeeded: $distExe"
} else {
    Write-Warning "Build finished but 'dist\windwoslh.exe' was not found. Check PyInstaller output above."
}

Pop-Location