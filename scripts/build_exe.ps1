$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $Root ".venv-gui\Scripts\python.exe"
$System32 = Join-Path $env:WINDIR "System32"
$PythonHome = Split-Path (Split-Path $Python -Parent) -Parent

if (!(Test-Path $Python)) {
    throw "Missing GUI environment: $Python"
}

Push-Location $Root
try {
    $env:PATH = @(
        (Split-Path $Python -Parent),
        $PythonHome,
        $System32,
        (Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0"),
        $env:WINDIR
    ) -join [IO.Path]::PathSeparator

    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --noupx `
        --name PrivCage `
        --collect-submodules PySide6.QtCore `
        --collect-submodules PySide6.QtGui `
        --collect-submodules PySide6.QtWidgets `
        --collect-data PySide6 `
        --collect-binaries PySide6 `
        --collect-binaries shiboken6 `
        --collect-all fitz `
        --add-binary "$System32\msvcp140.dll;." `
        --add-binary "$System32\msvcp140_1.dll;." `
        --add-binary "$System32\msvcp140_2.dll;." `
        --hidden-import docx `
        --hidden-import openpyxl `
        --hidden-import pptx `
        --hidden-import lxml `
        --hidden-import cryptography `
        --add-data "config.example;config.example" `
        --add-data "docs;docs" `
        "scripts\gui_entry.py"
} finally {
    Pop-Location
}
