# Build script for Windows (PowerShell)
# Usage: Right-click -> Run with PowerShell, or run: powershell -ExecutionPolicy Bypass -File .\build.ps1

$ErrorActionPreference = 'Stop'

# Ensure venv (optional). Comment out if you prefer global Python.
# python -m venv .venv
# . .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt

# Clean previous builds
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path SystemCheckPy.spec) { Remove-Item -Force SystemCheckPy.spec }

# Build GUI app (no console window)
$pyiArgs = @(
    '--noconfirm',
    '--clean',
    '--windowed',
    '--onefile',
    '--name', 'SystemCheckPy',
    'main.py'
)
pyinstaller @pyiArgs

Write-Host "Build finished. EXE path:" (Resolve-Path .\dist\SystemCheckPy.exe)
