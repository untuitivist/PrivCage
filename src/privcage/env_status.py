from __future__ import annotations

import importlib.util
import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    available: bool
    detail: str


def key_status() -> str:
    if os.environ.get("PRIVCAGE_MASTER_KEY"):
        return "PRIVCAGE_MASTER_KEY is set"
    key_file = os.environ.get("PRIVCAGE_KEY_FILE")
    if key_file:
        path = Path(key_file).expanduser()
        return f"PRIVCAGE_KEY_FILE: {path} ({'exists' if path.is_file() else 'missing'})"
    if os.environ.get("PRIVCAGE_ALLOW_DEMO_KEY") == "1":
        return "demo key enabled"
    return "missing key"


def dependency_statuses() -> list[DependencyStatus]:
    return [
        _module_status("python-docx", "docx"),
        _module_status("openpyxl", "openpyxl"),
        _module_status("python-pptx", "pptx"),
        _module_status("PyMuPDF", "fitz"),
        _binary_status("LibreOffice", "soffice"),
    ]


def _module_status(name: str, module: str) -> DependencyStatus:
    available = importlib.util.find_spec(module) is not None
    return DependencyStatus(name=name, available=available, detail="installed" if available else "not installed")


def _binary_status(name: str, binary: str) -> DependencyStatus:
    path = shutil.which(binary) or shutil.which("libreoffice")
    return DependencyStatus(name=name, available=path is not None, detail=path or "not found")
