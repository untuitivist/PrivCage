from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Hit:
    hit_id: str
    label: str
    text: str
    start: int
    end: int
    source: str


@dataclass(frozen=True)
class ParseResult:
    text: str
    assets: list[Path] = field(default_factory=list)
    source_kind: str = "text"


@dataclass(frozen=True)
class ProcessResult:
    source: Path
    output_dir: Path
    manifest_path: Path
    document_path: Path
    log_path: Path
    hits: int


@dataclass(frozen=True)
class UnprocessedResult:
    source: Path
    destination: Path
    stage: str
    reason: str


@dataclass(frozen=True)
class RestoreResult:
    input_path: Path
    output_path: Path
    restored_count: int
