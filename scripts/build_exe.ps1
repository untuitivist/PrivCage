$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root ".venv-gui\Scripts\python.exe"

if (!(Test-Path $Python)) {
    throw "Missing GUI environment: $Python"
}

Push-Location $Root
try {
    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name PrivCage `
        --collect-all PySide6 `
        --collect-all shiboken6 `
        --collect-all fitz `
        --hidden-import docx `
        --hidden-import openpyxl `
        --hidden-import pptx `
        --hidden-import lxml `
        --hidden-import cryptography `
        --add-data "config.example;config.example" `
        --add-data "docs;docs" `
        "src\privcage\gui_app.py"
} finally {
    Pop-Location
}
