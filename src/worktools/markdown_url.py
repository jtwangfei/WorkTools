"""Command-line interface for archiving article URLs as Markdown."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from collections.abc import Callable, Sequence
from pathlib import Path

from worktools.web_to_markdown import ArchiveError, ArchiveOptions, ArchiveResult, archive_url

ArchiveCallable = Callable[[str, ArchiveOptions], ArchiveResult]


def main(argv: Sequence[str] | None = None, *, archive: ArchiveCallable = archive_url) -> int:
    """Run the Markdown URL archiver CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    options = ArchiveOptions(
        output_dir=Path(args.output_dir),
        overwrite=args.overwrite,
        timeout=args.timeout,
        keep_links=args.keep_links,
    )

    try:
        result = archive(args.url, options)
    except ArchiveError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Saved Markdown: {result.markdown_path}")
    print(f"Saved images: {result.images_dir}")
    for warning in result.warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    return 0


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="python -m worktools.markdown_url",
        description="Archive a general article URL as Markdown with local body images.",
    )
    parser.add_argument("url", help="Article URL to archive.")
    parser.add_argument(
        "-o",
        "--output-dir",
        default="exports/markdown",
        help="Output root directory. Defaults to exports/markdown.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing article output folder.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Request timeout in seconds. Defaults to 20.",
    )
    parser.add_argument(
        "--keep-links",
        action="store_true",
        help="Keep normal hyperlinks in Markdown instead of converting them to plain text.",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
