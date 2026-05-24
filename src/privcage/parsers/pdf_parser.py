from __future__ import annotations

from pathlib import Path

from privcage.errors import ParseError
from privcage.models import ParseResult


def parse_pdf(path: Path, output_dir: Path) -> ParseResult:
    try:
        import fitz
    except ImportError as exc:
        raise ParseError("PyMuPDF is required for pdf files") from exc

    document = fitz.open(path)
    lines: list[str] = [f"# {path.name}"]
    assets: list[Path] = []
    for page_index in range(document.page_count):
        page = document.load_page(page_index)
        text = page.get_text("text").strip()
        lines.append(f"\n## Page {page_index + 1}")
        if text:
            lines.append(f"\n{text}")
            continue

        figures_dir = output_dir / "figures" / "pdf_pages"
        figures_dir.mkdir(parents=True, exist_ok=True)
        image_name = f"page-{page_index + 1:04d}.png"
        image_path = figures_dir / image_name
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        pixmap.save(image_path)
        assets.append(image_path)
        rel = image_path.relative_to(output_dir).as_posix()
        lines.append(f"\n![Page {page_index + 1}](./{rel})")
    return ParseResult(text="\n".join(lines), assets=assets, source_kind="pdf")
