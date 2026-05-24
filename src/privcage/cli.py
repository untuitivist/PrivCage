from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .errors import PrivCageError
from .processor import process_input
from .restore import restore_markdown, reveal_placeholder


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="privcage")
    parser.add_argument("--input", help="input file or directory; compatibility alias for preprocess --input")
    parser.add_argument("--output", help="output root directory; compatibility alias for preprocess --output")
    parser.add_argument("--print-log", action="store_true", help="print ordinary processing logs to console")
    parser.add_argument(
        "--centralize-unprocessed",
        action="store_true",
        help="copy unprocessed files to .privcage/source_root.privacy/unprocessed/<relative-path>",
    )
    subparsers = parser.add_subparsers(dest="command")

    preprocess = subparsers.add_parser("preprocess", help="create .privacy artifacts")
    preprocess.add_argument("--input", required=True, help="input file or directory")
    preprocess.add_argument("--output", required=True, help="output root directory")
    preprocess.add_argument("--print-log", action="store_true", help="print ordinary processing logs to console")
    preprocess.add_argument(
        "--centralize-unprocessed",
        action="store_true",
        help="copy unprocessed files to .privcage/source_root.privacy/unprocessed/<relative-path>",
    )

    restore = subparsers.add_parser("restore", help="restore placeholders in a Markdown file")
    restore.add_argument("--privacy", required=True, help=".privacy artifact directory; can be a file artifact or a batch root")
    restore.add_argument("--input", required=True, help="AI-processed Markdown file")
    restore.add_argument("--output", help="restored Markdown output path; defaults to <privacy>/{source_or_root_name}_restored.md")
    restore.add_argument("--print-log", action="store_true", help="print ordinary restore logs to console")

    reveal = subparsers.add_parser("reveal", help="print the plaintext for one PRIVACY placeholder")
    reveal.add_argument("--privacy", required=True, help=".privacy artifact directory; can be a file artifact or a batch root")
    reveal.add_argument("--placeholder", required=True, help="full [PRIVACY:{TYPE}:{cipher_blob}] placeholder")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config()
        if args.command == "restore":
            result = restore_markdown(
                privacy_dir=Path(args.privacy),
                input_path=Path(args.input),
                output_path=Path(args.output) if args.output else None,
                config=config,
            )
            if args.print_log:
                print(f"restored: {result.input_path} -> {result.output_path} ({result.restored_count} placeholders)")
            return 0
        if args.command == "reveal":
            print(reveal_placeholder(Path(args.privacy), args.placeholder, config))
            return 0

        input_arg = args.input
        output_arg = args.output
        if not input_arg or not output_arg:
            parser.error("--input and --output are required")
        processed, unprocessed = process_input(
            input_path=Path(input_arg),
            output_root=Path(output_arg),
            config=config,
            centralize_unprocessed=args.centralize_unprocessed,
        )
    except PrivCageError as exc:
        print(f"privcage: {exc}", file=sys.stderr)
        return 2

    if args.print_log:
        for item in processed:
            print(f"processed: {item.source} -> {item.output_dir} ({item.hits} hits)")

    for item in unprocessed:
        print(
            "unprocessed: "
            f"path={item.source} stage={item.stage} reason={item.reason} destination={item.destination}",
            file=sys.stderr,
        )

    return 1 if unprocessed and not processed else 0
