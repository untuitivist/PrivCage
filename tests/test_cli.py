from __future__ import annotations

import json
from pathlib import Path

from privcage.cli import main
from privcage.encoding import b64url_encode


def test_cli_preprocess_and_restore(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PRIVCAGE_MASTER_KEY", b64url_encode(b"6" * 32))
    source = tmp_path / "sample.txt"
    source.write_text("Email alice@example.com.", encoding="utf-8")

    preprocess_code = main(["preprocess", "--input", str(source), "--output", str(tmp_path / "out")])

    assert preprocess_code == 0
    privacy_dir = tmp_path / "out" / "sample.txt.privacy"
    restore_code = main(
        [
            "restore",
            "--privacy",
            str(privacy_dir),
            "--input",
            str(privacy_dir / "document.md"),
        ]
    )

    restored = privacy_dir / "sample.txt_restored.md"
    assert restore_code == 0
    assert "alice@example.com" in restored.read_text(encoding="utf-8")


def test_cli_reveal_placeholder(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("PRIVCAGE_MASTER_KEY", b64url_encode(b"7" * 32))
    source = tmp_path / "sample.txt"
    source.write_text("Email alice@example.com.", encoding="utf-8")

    assert main(["preprocess", "--input", str(source), "--output", str(tmp_path / "out")]) == 0
    privacy_dir = tmp_path / "out" / "sample.txt.privacy"
    manifest = json.loads((tmp_path / "out" / ".privcage" / "sample.txt.privacy" / "manifest.json").read_text(encoding="utf-8"))
    placeholder = manifest["hits"][0]["privacy_placeholder"]

    reveal_code = main(["reveal", "--privacy", str(privacy_dir), "--placeholder", placeholder])

    captured = capsys.readouterr()
    assert reveal_code == 0
    assert captured.out == "alice@example.com\n"
