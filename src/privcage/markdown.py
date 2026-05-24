from __future__ import annotations


def render_document(body: str) -> str:
    return (
        "---\n"
        "document_type: privacy-protected-markdown\n"
        "protocol_version: v1\n"
        "encryption:\n"
        "  algorithm: AES-256-GCM\n"
        "  key_policy: env-or-user-config-key-in-intranet\n"
        "  nonce_policy: random-per-fragment\n"
        "  cipher_blob: base64url-json-envelope\n"
        "placeholder:\n"
        '  format: "[PRIVACY:{TYPE}:{cipher_blob}]"\n'
        "assets:\n"
        '  figures_dir: "./figures"\n'
        '  attachments_dir: "./attachments"\n'
        "processing_notice:\n"
        '  - "Do not modify PRIVACY placeholders."\n'
        "---\n\n"
        f"{body.rstrip()}\n"
    )
