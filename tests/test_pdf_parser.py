from __future__ import annotations

from pathlib import Path

import fitz

from privcage.parsers.pdf_parser import parse_pdf


def test_text_pdf_outputs_text_without_page_image(tmp_path: Path) -> None:
    pdf_path = tmp_path / "text.pdf"
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((30, 50), "Contact alice@example.com", fontsize=12)
    document.save(pdf_path)
    document.close()

    result = parse_pdf(pdf_path, tmp_path / "out")

    assert "Contact alice@example.com" in result.text
    assert "![Page 1]" not in result.text
    assert result.assets == []
    assert not (tmp_path / "out" / "figures" / "pdf_pages").exists()


def test_image_pdf_outputs_page_image_reference(tmp_path: Path) -> None:
    pdf_path = tmp_path / "image.pdf"
    document = fitz.open()
    document.new_page(width=300, height=200)
    document.save(pdf_path)
    document.close()

    result = parse_pdf(pdf_path, tmp_path / "out")

    assert "![Page 1](./figures/pdf_pages/page-0001.png)" in result.text
    assert len(result.assets) == 1
    assert (tmp_path / "out" / "figures" / "pdf_pages" / "page-0001.png").is_file()
