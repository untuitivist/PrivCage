from __future__ import annotations

from .crypto import CryptoContext, encrypt_placeholder_payload
from .hashing import sha256_text
from .models import Hit


def apply_placeholders(text: str, hits: list[Hit], context: CryptoContext) -> tuple[str, list[dict[str, object]]]:
    chunks: list[str] = []
    records: list[dict[str, object]] = []
    cursor = 0

    for hit in hits:
        chunks.append(text[cursor : hit.start])
        payload = {"text": hit.text, "hit_id": hit.hit_id, "label": hit.label}
        cipher_blob = encrypt_placeholder_payload(payload, hit.label, context)
        placeholder = f"[PRIVACY:{hit.label}:{cipher_blob}]"
        chunks.append(placeholder)
        cursor = hit.end
        records.append(
            {
                "hit_id": hit.hit_id,
                "source": hit.source,
                "label": hit.label,
                "text_hash": sha256_text(hit.text),
                "position": {"start": hit.start, "end": hit.end},
                "placeholder_type": hit.label,
                "privacy_placeholder": placeholder,
            }
        )

    chunks.append(text[cursor:])
    return "".join(chunks), records
