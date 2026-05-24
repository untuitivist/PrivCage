from __future__ import annotations

import re

from .models import Hit

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d -]{7,}\d)(?!\d)")
ID_RE = re.compile(r"\b\d{15}(\d{2}[0-9Xx])?\b")


def recognize(text: str) -> list[Hit]:
    candidates: list[tuple[str, str, int, int]] = []
    candidates.extend(("EMAIL", match.group(), match.start(), match.end()) for match in EMAIL_RE.finditer(text))
    candidates.extend(("PHONE", match.group(), match.start(), match.end()) for match in PHONE_RE.finditer(text))
    candidates.extend(("ID", match.group(), match.start(), match.end()) for match in ID_RE.finditer(text))

    candidates.sort(key=lambda item: (item[2], -(item[3] - item[2])))
    hits: list[Hit] = []
    occupied_end = -1
    for index, (label, value, start, end) in enumerate(candidates, start=1):
        if start < occupied_end:
            continue
        hits.append(Hit(hit_id=f"h{index:04d}", label=label, text=value, start=start, end=end, source="rule"))
        occupied_end = end
    return hits
