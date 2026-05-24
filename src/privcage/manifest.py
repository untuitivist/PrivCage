from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_manifest(
    privacy_id: str,
    source_name: str,
    source_type: str,
    source_hash: str,
    hits: list[dict[str, object]],
) -> dict[str, Any]:
    return {
        "protocol_version": "v1",
        "privacy_id": privacy_id,
        "source_file": {"name": source_name, "type": source_type, "sha256": source_hash},
        "artifacts": {
            "document": "document.md",
            "figures_dir": "figures/",
            "attachments_dir": "attachments/",
            "restore_index": "restore/index.json",
            "process_log": "process.log",
        },
        "recognition": {
            "pipeline": ["rule", "spacy", "transformers"],
            "enabled": {"rule": True, "spacy": False, "transformers": False},
        },
        "hits": hits,
        "restore_targets": [f"{source_name}_restored.md"],
    }


def build_restore_index(source_name: str, source_hash: str, hits: list[dict[str, object]]) -> dict[str, Any]:
    return {
        "version": 1,
        "source_file": source_name,
        "source_hash": source_hash,
        "document": "document.md",
        "placeholders": [
            {
                "hit_id": hit["hit_id"],
                "privacy_placeholder": hit["privacy_placeholder"],
                "source_anchor": {"kind": "markdown_text"},
                "source_range": hit["position"],
                "text_hash": hit["text_hash"],
                "placeholder_type": hit["placeholder_type"],
            }
            for hit in hits
        ],
    }
