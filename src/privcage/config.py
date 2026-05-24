from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .encoding import b64url_decode
from .errors import ConfigError


@dataclass(frozen=True)
class AppConfig:
    master_key: bytes
    key_id: str = "default"


def load_config() -> AppConfig:
    key_id = os.environ.get("PRIVCAGE_KEY_ID", "default")
    key_text = os.environ.get("PRIVCAGE_MASTER_KEY")

    if key_text:
        return AppConfig(master_key=_decode_key(key_text), key_id=key_id)

    key_file = os.environ.get("PRIVCAGE_KEY_FILE")
    if key_file:
        path = Path(key_file).expanduser()
        if not path.is_file():
            raise ConfigError(f"key file does not exist: {path}")
        return AppConfig(master_key=_decode_key(path.read_text(encoding="utf-8").strip()), key_id=key_id)

    demo_key = os.environ.get("PRIVCAGE_ALLOW_DEMO_KEY")
    if demo_key == "1":
        return AppConfig(master_key=b"\0" * 32, key_id="demo")

    raise ConfigError(
        "missing key: set PRIVCAGE_MASTER_KEY or PRIVCAGE_KEY_FILE; "
        "for tests only, set PRIVCAGE_ALLOW_DEMO_KEY=1"
    )


def _decode_key(text: str) -> bytes:
    try:
        key = b64url_decode(text)
    except Exception as exc:  # noqa: BLE001
        raise ConfigError("master key must be base64url encoded") from exc
    if len(key) != 32:
        raise ConfigError("master key must decode to exactly 32 bytes")
    return key
