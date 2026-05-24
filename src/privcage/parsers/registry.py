from __future__ import annotations

from pathlib import Path

from privcage.errors import ParseError
from privcage.models import ParseResult

from .legacy_office_parser import parse_legacy_office
from .office_parser import parse_docx, parse_pptx, parse_xlsx
from .pdf_parser import parse_pdf
from .text_parser import parse_text_like


def parse_file(path: Path, output_dir: Path) -> ParseResult:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".rtf"}:
        return parse_text_like(path)
    if suffix == ".docx":
        return parse_docx(path)
    if suffix == ".xlsx":
        return parse_xlsx(path)
    if suffix in {".doc", ".xls", ".ppt"}:
        return parse_legacy_office(path, output_dir)
    if suffix == ".pdf":
        return parse_pdf(path, output_dir)
    if suffix == ".pptx":
        return parse_pptx(path)
    raise ParseError(f"unsupported file type: {suffix or '<none>'}")
