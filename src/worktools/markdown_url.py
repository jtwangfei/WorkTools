"""Command-line interface for archiving article URLs as Markdown."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from collections.abc import Callable, Sequence
from pathlib import Path

from worktools.web_to_markdown import (
    ArchiveError,
    ArchiveOptions,
    ArchiveResult,
    archive_url,
)
from worktools.web_to_markdown import (
    archive_html_file as archive_saved_html_file,
)

ArchiveCallable = Callable[[str, ArchiveOptions], ArchiveResult]
HtmlFileArchiveCallable = Callable[[Path, ArchiveOptions, str | None], ArchiveResult]


def main(
    argv: Sequence[str] | None = None,
    *,
    archive: ArchiveCallable = archive_url,
    archive_html_file: HtmlFileArchiveCallable = archive_saved_html_file,
) -> int:
    """Run the Markdown URL archiver CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.html_file and args.url:
        parser.error("provide either a URL or --html-file, not both")
    if not args.html_file and not args.url:
        parser.error("a URL is required unless --html-file is used")

    options = ArchiveOptions(
        output_dir=Path(args.output_dir),
        overwrite=args.overwrite,
        timeout=args.timeout,
        keep_links=args.keep_links,
    )

    try:
        if args.html_file:
            result = archive_html_file(Path(args.html_file), options, args.source_url)
        else:
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
    parser.add_argument("url", nargs="?", help="Article URL to archive.")
    parser.add_argument(
        "--html-file",
        help="Convert a saved HTML file instead of fetching a URL.",
    )
    parser.add_argument(
        "--source-url",
        help="Original page URL for resolving relative links when --html-file is used.",
    )
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
