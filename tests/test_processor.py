from __future__ import annotations

import json
from pathlib import Path

from privcage.config import AppConfig
from privcage.processor import process_input
from privcage.restore import restore_markdown


def test_process_text_file(tmp_path: Path) -> None:
    source = tmp_path / "meeting.txt"
    source.write_text("Contact alice@example.com or +1 555 123 4567.", encoding="utf-8")

    processed, unprocessed = process_input(source, tmp_path / "out", AppConfig(master_key=b"2" * 32))

    assert not unprocessed
    assert len(processed) == 1
    output_dir = tmp_path / "out" / "meeting.txt.privacy"
    document = (output_dir / "document.md").read_text(encoding="utf-8")
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    restore_index = json.loads((output_dir / "restore" / "index.json").read_text(encoding="utf-8"))

    assert "[PRIVACY:EMAIL:" in document
    assert "[PRIVACY:PHONE:" in document
    assert manifest["privacy_id"] == "meeting.txt.privacy"
    assert (output_dir / "process.log").is_file()
    assert len(restore_index["placeholders"]) == 2


def test_restore_markdown_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "meeting.txt"
    source.write_text("Contact alice@example.com.", encoding="utf-8")
    config = AppConfig(master_key=b"2" * 32)

    process_input(source, tmp_path / "out", config)
    privacy_dir = tmp_path / "out" / "meeting.txt.privacy"
    ai_result = tmp_path / "ai-result.md"
    ai_result.write_text((privacy_dir / "document.md").read_text(encoding="utf-8"), encoding="utf-8")
    restored = tmp_path / "restored.md"

    result = restore_markdown(privacy_dir, ai_result, restored, config)

    assert result.restored_count == 1
    assert "alice@example.com" in restored.read_text(encoding="utf-8")


def test_unprocessed_default_keeps_relative_path(tmp_path: Path) -> None:
    source_root = tmp_path / "source_root"
    source_file = source_root / "A" / "B" / "bad.bin"
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(b"\x00\x01")

    processed, unprocessed = process_input(source_root, tmp_path / "out", AppConfig(master_key=b"3" * 32))

    assert not processed
    assert len(unprocessed) == 1
    assert unprocessed[0].destination == tmp_path / "out" / "source_root.privacy" / "A" / "B" / "bad.bin"
    assert unprocessed[0].destination.read_bytes() == b"\x00\x01"


def test_unprocessed_centralized_keeps_relative_path(tmp_path: Path) -> None:
    source_root = tmp_path / "source_root"
    source_file = source_root / "A" / "B" / "bad.bin"
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(b"\x00\x01")

    processed, unprocessed = process_input(
        source_root,
        tmp_path / "out",
        AppConfig(master_key=b"4" * 32),
        centralize_unprocessed=True,
    )

    assert not processed
    assert len(unprocessed) == 1
    assert unprocessed[0].destination == tmp_path / "out" / "source_root.privacy" / "unprocessed" / "A" / "B" / "bad.bin"
    assert unprocessed[0].destination.read_bytes() == b"\x00\x01"
