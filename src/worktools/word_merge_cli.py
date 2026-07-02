from __future__ import annotations

import argparse
from pathlib import Path

from worktools.word_merge import WordMergeError, WordMergeOptions, merge_documents


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Merge Word documents into a template.")
    parser.add_argument("--template", required=True, help="Template name or .docx/.dotx path.")
    parser.add_argument("inputs", nargs="+", help="Input .docx files.")
    parser.add_argument("-o", "--output", required=True, help="Output .docx path.")
    parser.add_argument(
        "--mode",
        choices=["direct", "summarize"],
        default="direct",
        help="Merge mode. summarize is reserved for a future version.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = merge_documents(
            WordMergeOptions(
                template=args.template,
                inputs=[Path(input_path) for input_path in args.inputs],
                output=Path(args.output),
                mode=args.mode,
                overwrite=args.overwrite,
            )
        )
    except WordMergeError as error:
        parser.error(str(error))

    print(f"Merged document written to {result.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
