from __future__ import annotations

import json
from pathlib import Path

from .config import AppConfig
from .crypto import CryptoContext, decrypt_placeholder_payload
from .errors import PrivCageError
from .models import RestoreResult


def restore_markdown(privacy_dir: Path, input_path: Path, output_path: Path, config: AppConfig) -> RestoreResult:
    privacy_dir = privacy_dir.resolve()
    input_path = input_path.resolve()
    output_path = output_path.resolve()

    manifest_path = privacy_dir / "manifest.json"
    restore_index_path = privacy_dir / "restore" / "index.json"
    if not manifest_path.is_file():
        raise PrivCageError(f"manifest not found: {manifest_path}")
    if not restore_index_path.is_file():
        raise PrivCageError(f"restore index not found: {restore_index_path}")
    if not input_path.is_file():
        raise PrivCageError(f"restore input not found: {input_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    restore_index = json.loads(restore_index_path.read_text(encoding="utf-8"))
    text = input_path.read_text(encoding="utf-8")

    context = CryptoContext(
        key=config.master_key,
        key_id=config.key_id,
        protocol_version=manifest["protocol_version"],
        privacy_id=manifest["privacy_id"],
        source_hash=manifest["source_file"]["sha256"],
    )

    restored_count = 0
    for item in restore_index.get("placeholders", []):
        placeholder = item["privacy_placeholder"]
        hit_id = item["hit_id"]
        placeholder_type = item["placeholder_type"]
        if placeholder not in text:
            continue
        cipher_blob = _extract_cipher_blob(placeholder)
        payload = decrypt_placeholder_payload(cipher_blob, hit_id, placeholder_type, context)
        text = text.replace(placeholder, payload["text"])
        restored_count += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    _append_log(privacy_dir / "process.log", f"restored input={input_path} output={output_path} count={restored_count}")
    return RestoreResult(input_path=input_path, output_path=output_path, restored_count=restored_count)


def _extract_cipher_blob(placeholder: str) -> str:
    if not (placeholder.startswith("[PRIVACY:") and placeholder.endswith("]")):
        raise PrivCageError("invalid placeholder format in restore index")
    parts = placeholder.removeprefix("[PRIVACY:").removesuffix("]").split(":", 1)
    if len(parts) != 2:
        raise PrivCageError("invalid placeholder format in restore index")
    return parts[1]


def _append_log(path: Path, message: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")
