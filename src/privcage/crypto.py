from __future__ import annotations

import json
import secrets
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .encoding import b64url_decode, b64url_encode


@dataclass(frozen=True)
class CryptoContext:
    key: bytes
    key_id: str
    protocol_version: str
    privacy_id: str
    source_hash: str


def encrypt_placeholder_payload(
    payload: dict[str, str],
    placeholder_type: str,
    context: CryptoContext,
) -> str:
    nonce = secrets.token_bytes(12)
    aad = _aad(context, payload["hit_id"], placeholder_type)
    plaintext = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ciphertext = AESGCM(context.key).encrypt(nonce, plaintext, aad)
    envelope = {
        "v": 1,
        "alg": "A256GCM",
        "kid": context.key_id,
        "n": b64url_encode(nonce),
        "c": b64url_encode(ciphertext),
    }
    raw = json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return b64url_encode(raw)


def decrypt_placeholder_payload(
    cipher_blob: str,
    hit_id: str,
    placeholder_type: str,
    context: CryptoContext,
) -> dict[str, str]:
    envelope = json.loads(b64url_decode(cipher_blob).decode("utf-8"))
    if envelope.get("v") != 1 or envelope.get("alg") != "A256GCM":
        raise ValueError("unsupported cipher envelope")
    nonce = b64url_decode(envelope["n"])
    ciphertext = b64url_decode(envelope["c"])
    aad = _aad(context, hit_id, placeholder_type)
    plaintext = AESGCM(context.key).decrypt(nonce, ciphertext, aad)
    return json.loads(plaintext.decode("utf-8"))


def _aad(context: CryptoContext, hit_id: str, placeholder_type: str) -> bytes:
    aad = {
        "protocol_version": context.protocol_version,
        "privacy_id": context.privacy_id,
        "hit_id": hit_id,
        "placeholder_type": placeholder_type,
        "source_hash": context.source_hash,
    }
    return json.dumps(aad, sort_keys=True, separators=(",", ":")).encode("utf-8")
