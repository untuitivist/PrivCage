from __future__ import annotations

import json
from pathlib import Path

from .config import AppConfig
from .crypto import CryptoContext, decrypt_placeholder_payload
from .errors import PrivCageError
from .models import RestoreResult


def restore_markdown(
    privacy_dir: Path,
    input_path: Path,
    output_path: Path | None,
    config: AppConfig,
) -> RestoreResult:
    privacy_dir = privacy_dir.resolve()
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise PrivCageError(f"restore input not found: {input_path}")

    contexts = _restore_contexts_for_privacy_dir(privacy_dir)
    output_path = (output_path or privacy_dir / _default_restored_name(privacy_dir, contexts)).resolve()
    text = input_path.read_text(encoding="utf-8")

    restored_count = 0
    touched_logs: set[Path] = set()
    for restore_context in contexts:
        context = _build_crypto_context(restore_context["manifest"], config)
        for item in restore_context["restore_index"].get("placeholders", []):
            placeholder = item["privacy_placeholder"]
            hit_id = item["hit_id"]
            placeholder_type = item["placeholder_type"]
            if placeholder not in text:
                continue
            cipher_blob = _extract_cipher_blob(placeholder)
            payload = decrypt_placeholder_payload(cipher_blob, hit_id, placeholder_type, context)
            text = text.replace(placeholder, payload["text"])
            restored_count += 1
            touched_logs.add(restore_context["state_dir"] / "process.log")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    if not touched_logs:
        touched_logs = {contexts[0]["state_dir"] / "process.log"}
    for log_path in touched_logs:
        _append_log(log_path, f"restored input={input_path} output={output_path} count={restored_count}")
    return RestoreResult(input_path=input_path, output_path=output_path, restored_count=restored_count)


def reveal_placeholder(privacy_dir: Path, placeholder: str, config: AppConfig) -> str:
    privacy_dir = privacy_dir.resolve()
    for restore_context in _restore_contexts_for_privacy_dir(privacy_dir):
        try:
            item = _find_placeholder(restore_context["restore_index"], placeholder)
        except PrivCageError:
            continue
        context = _build_crypto_context(restore_context["manifest"], config)
        cipher_blob = _extract_cipher_blob(placeholder)
        payload = decrypt_placeholder_payload(cipher_blob, item["hit_id"], item["placeholder_type"], context)
        return payload["text"]
    raise PrivCageError("placeholder not found in restore index")


def _load_restore_context(state_dir: Path) -> tuple[dict, dict]:
    manifest_path = state_dir / "manifest.json"
    restore_index_path = state_dir / "restore" / "index.json"
    if not manifest_path.is_file():
        raise PrivCageError(f"manifest not found: {manifest_path}")
    if not restore_index_path.is_file():
        raise PrivCageError(f"restore index not found: {restore_index_path}")
    return (
        json.loads(manifest_path.read_text(encoding="utf-8")),
        json.loads(restore_index_path.read_text(encoding="utf-8")),
    )


def _restore_contexts_for_privacy_dir(privacy_dir: Path) -> list[dict]:
    state_dir = _state_dir_for_privacy_dir(privacy_dir)
    if (state_dir / "manifest.json").is_file():
        manifest, restore_index = _load_restore_context(state_dir)
        return [{"public_dir": privacy_dir, "state_dir": state_dir, "manifest": manifest, "restore_index": restore_index}]

    if not state_dir.is_dir():
        raise PrivCageError(f"state directory not found: {state_dir}")

    public_root = _public_root_for_privacy_dir(privacy_dir)
    output_root = public_root.parent
    state_root = output_root / ".privcage"
    contexts: list[dict] = []
    for manifest_path in sorted(state_dir.rglob("manifest.json")):
        child_state_dir = manifest_path.parent
        restore_index_path = child_state_dir / "restore" / "index.json"
        if not restore_index_path.is_file():
            continue
        child_public_dir = output_root / child_state_dir.relative_to(state_root)
        if not child_public_dir.is_dir():
            continue
        manifest, restore_index = _load_restore_context(child_state_dir)
        contexts.append(
            {
                "public_dir": child_public_dir,
                "state_dir": child_state_dir,
                "manifest": manifest,
                "restore_index": restore_index,
            }
        )
    if not contexts:
        raise PrivCageError(f"no restore indexes found under: {state_dir}")
    return contexts


def _state_dir_for_privacy_dir(privacy_dir: Path) -> Path:
    public_root = _public_root_for_privacy_dir(privacy_dir)
    output_root = public_root.parent
    relative = privacy_dir.relative_to(output_root)
    return output_root / ".privcage" / relative


def _public_root_for_privacy_dir(privacy_dir: Path) -> Path:
    privacy_ancestors = [path for path in (privacy_dir, *privacy_dir.parents) if path.name.endswith(".privacy")]
    if not privacy_ancestors:
        raise PrivCageError(f"not a .privacy directory: {privacy_dir}")
    return privacy_ancestors[-1]


def _build_crypto_context(manifest: dict, config: AppConfig) -> CryptoContext:
    return CryptoContext(
        key=config.master_key,
        key_id=config.key_id,
        protocol_version=manifest["protocol_version"],
        privacy_id=manifest["privacy_id"],
        source_hash=manifest["source_file"]["sha256"],
    )


def _find_placeholder(restore_index: dict, placeholder: str) -> dict:
    for item in restore_index.get("placeholders", []):
        if item["privacy_placeholder"] == placeholder:
            return item
    raise PrivCageError("placeholder not found in restore index")


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


def _default_restored_name(privacy_dir: Path, contexts: list[dict]) -> str:
    if len(contexts) == 1 and contexts[0]["public_dir"] == privacy_dir:
        source_name = contexts[0]["manifest"].get("source_file", {}).get("name") or "restored"
        return f"{source_name}_restored.md"
    source_name = privacy_dir.name.removesuffix(".privacy") or "restored"
    return f"{source_name}_restored.md"
