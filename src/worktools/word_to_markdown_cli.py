"""Command-line interface for converting Word documents to Markdown."""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from collections.abc import Callable, Sequence
from pathlib import Path

from worktools.word_to_markdown import (
    WordToMarkdownError,
    WordToMarkdownOptions,
    WordToMarkdownResult,
    convert_word_to_markdown,
)

ConvertCallable = Callable[[WordToMarkdownOptions], WordToMarkdownResult]


def main(
    argv: Sequence[str] | None = None,
    *,
    converter: ConvertCallable = convert_word_to_markdown,
) -> int:
    """Run the Word to Markdown converter CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    options = WordToMarkdownOptions(
        input_path=Path(args.input),
        output=Path(args.output) if args.output else None,
        overwrite=args.overwrite,
    )

    try:
        result = converter(options)
    except WordToMarkdownError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Saved Markdown: {result.markdown_path}")
    print(f"Saved media: {result.media_dir}")
    return 0


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="python -m worktools.word_to_markdown_cli",
        description="Convert a Word .docx file to Markdown using Pandoc.",
    )
    parser.add_argument("input", help="Input .docx file.")
    parser.add_argument("-o", "--output", help="Output .md file.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing Markdown output file.",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
