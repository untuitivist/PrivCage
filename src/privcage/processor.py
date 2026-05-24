from __future__ import annotations

import shutil
from pathlib import Path

from .config import AppConfig
from .crypto import CryptoContext
from .errors import ParseError, PrivCageError
from .hashing import sha256_file
from .manifest import build_manifest, build_restore_index, write_json
from .markdown import render_document
from .models import ProcessResult, UnprocessedResult
from .parsers import parse_file
from .placeholder import apply_placeholders
from .recognize import recognize


def process_input(
    input_path: Path,
    output_root: Path,
    config: AppConfig,
    centralize_unprocessed: bool = False,
) -> tuple[list[ProcessResult], list[UnprocessedResult]]:
    input_path = input_path.resolve()
    output_root = output_root.resolve()
    if input_path.is_file():
        output_base = output_root / f"{input_path.name}.privacy"
        state_base = output_root / ".privcage" / output_base.name
        return _process_files(
            [input_path],
            input_path.parent,
            output_base,
            state_base,
            config,
            centralize_unprocessed,
            single_file=True,
        )
    if input_path.is_dir():
        output_base = output_root / f"{input_path.name}.privacy"
        state_base = output_root / ".privcage" / output_base.name
        files = [path for path in input_path.rglob("*") if path.is_file()]
        return _process_files(files, input_path, output_base, state_base, config, centralize_unprocessed, single_file=False)
    raise PrivCageError(f"input does not exist: {input_path}")


def _process_files(
    files: list[Path],
    source_root: Path,
    output_base: Path,
    state_base: Path,
    config: AppConfig,
    centralize_unprocessed: bool,
    single_file: bool,
) -> tuple[list[ProcessResult], list[UnprocessedResult]]:
    processed: list[ProcessResult] = []
    unprocessed: list[UnprocessedResult] = []
    output_base.mkdir(parents=True, exist_ok=True)
    state_base.mkdir(parents=True, exist_ok=True)

    for source in files:
        relative = Path(source.name) if single_file else source.relative_to(source_root)
        output_dir = output_base if single_file else output_base / relative.parent / f"{source.name}.privacy"
        state_dir = state_base if single_file else state_base / relative.parent / f"{source.name}.privacy"
        try:
            processed.append(_process_one(source, output_dir, state_dir, config))
        except Exception as exc:  # noqa: BLE001
            reason = str(exc) or exc.__class__.__name__
            destination = _copy_unprocessed(source, state_base, relative, centralize_unprocessed, single_file)
            unprocessed.append(UnprocessedResult(source=source, destination=destination, stage="parse", reason=reason))

    return processed, unprocessed


def _process_one(source: Path, output_dir: Path, state_dir: Path, config: AppConfig) -> ProcessResult:
    _ensure_public_dirs(output_dir)
    _ensure_state_dirs(state_dir)
    source_hash = sha256_file(source)
    parse_result = parse_file(source, output_dir)
    privacy_id = output_dir.name
    context = CryptoContext(
        key=config.master_key,
        key_id=config.key_id,
        protocol_version="v1",
        privacy_id=privacy_id,
        source_hash=source_hash,
    )
    hits = recognize(parse_result.text)
    redacted, hit_records = apply_placeholders(parse_result.text, hits, context)

    document_path = output_dir / "document.md"
    manifest_path = state_dir / "manifest.json"
    restore_index_path = state_dir / "restore" / "index.json"
    log_path = state_dir / "process.log"

    document_path.write_text(render_document(redacted), encoding="utf-8")
    manifest = build_manifest(privacy_id, source.name, source.suffix.lower().lstrip("."), source_hash, hit_records)
    restore_index = build_restore_index(source.name, source_hash, hit_records)
    write_json(manifest_path, manifest)
    write_json(restore_index_path, restore_index)
    _append_log(log_path, f"processed source={source} hits={len(hit_records)} document={document_path}")

    return ProcessResult(
        source=source,
        output_dir=output_dir,
        state_dir=state_dir,
        manifest_path=manifest_path,
        document_path=document_path,
        log_path=log_path,
        hits=len(hit_records),
    )


def _copy_unprocessed(
    source: Path,
    state_base: Path,
    relative: Path,
    centralize_unprocessed: bool,
    single_file: bool,
) -> Path:
    if single_file:
        destination = state_base / "unprocessed" / source.name
    elif centralize_unprocessed:
        destination = state_base / "unprocessed" / relative
    else:
        destination = state_base / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def _ensure_public_dirs(output_dir: Path) -> None:
    for name in ("figures", "attachments"):
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def _ensure_state_dirs(state_dir: Path) -> None:
    for name in ("restore", "unprocessed"):
        (state_dir / name).mkdir(parents=True, exist_ok=True)


def _append_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")
