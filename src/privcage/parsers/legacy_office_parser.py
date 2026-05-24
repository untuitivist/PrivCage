from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from privcage.errors import ParseError
from privcage.models import ParseResult

from .office_parser import parse_docx, parse_xlsx


def parse_legacy_office(path: Path, output_dir: Path) -> ParseResult:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise ParseError("LibreOffice is required for legacy Office files")

    target_ext = _target_ext(path.suffix.lower())
    with tempfile.TemporaryDirectory(dir=output_dir) as temp_dir:
        temp = Path(temp_dir)
        command = [
            soffice,
            "--headless",
            "--convert-to",
            target_ext.lstrip("."),
            "--outdir",
            str(temp),
            str(path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            reason = completed.stderr.strip() or completed.stdout.strip() or "conversion failed"
            raise ParseError(reason)
        converted = temp / f"{path.stem}{target_ext}"
        if not converted.exists():
            matches = list(temp.glob(f"*{target_ext}"))
            if not matches:
                raise ParseError("converted file was not produced")
            converted = matches[0]
        if target_ext == ".docx":
            return parse_docx(converted)
        if target_ext == ".xlsx":
            return parse_xlsx(converted)
        raise ParseError("legacy ppt conversion target is not implemented")


def _target_ext(suffix: str) -> str:
    if suffix == ".doc":
        return ".docx"
    if suffix == ".xls":
        return ".xlsx"
    if suffix == ".ppt":
        return ".pptx"
    raise ParseError(f"unsupported legacy Office type: {suffix}")
