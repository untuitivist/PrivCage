from __future__ import annotations

from .cli import main


def run() -> int:
    """Thin GUI placeholder that delegates to the CLI pipeline.

    The packaged executable can point here while a real UI shell is developed.
    """
    return main()
