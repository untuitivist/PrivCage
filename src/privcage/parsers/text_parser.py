from __future__ import annotations

from pathlib import Path

from privcage.errors import ParseError
from privcage.models import ParseResult


def parse_text_like(path: Path) -> ParseResult:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            text = path.read_text(encoding=encoding)
            return ParseResult(text=text, source_kind=path.suffix.lower().lstrip(".") or "text")
        except UnicodeDecodeError:
            continue
    raise ParseError("could not decode text file")
