from __future__ import annotations

from privcage.crypto import CryptoContext, decrypt_placeholder_payload, encrypt_placeholder_payload


def test_encrypt_decrypt_placeholder_payload() -> None:
    context = CryptoContext(
        key=b"1" * 32,
        key_id="test",
        protocol_version="v1",
        privacy_id="sample.txt.privacy",
        source_hash="abc",
    )
    payload = {"text": "alice@example.com", "hit_id": "h0001", "label": "EMAIL"}

    blob = encrypt_placeholder_payload(payload, "EMAIL", context)
    restored = decrypt_placeholder_payload(blob, "h0001", "EMAIL", context)

    assert restored == payload
