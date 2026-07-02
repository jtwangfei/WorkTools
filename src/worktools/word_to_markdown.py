from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from subprocess import CalledProcessError


class WordToMarkdownError(RuntimeError):
    """Base error for Word to Markdown conversion failures."""


class InputDocumentError(WordToMarkdownError):
    """Raised when the input document is invalid."""


class OutputExistsError(WordToMarkdownError):
    """Raised when the output already exists and overwrite is disabled."""


class PandocNotFoundError(WordToMarkdownError):
    """Raised when the pandoc executable cannot be found."""


class PandocConversionError(WordToMarkdownError):
    """Raised when pandoc fails to convert the document."""


@dataclass(frozen=True)
class WordToMarkdownOptions:
    input_path: Path
    output: Path | None = None
    overwrite: bool = False
    output_dir: Path = Path("exports/markdown")


@dataclass(frozen=True)
class WordToMarkdownResult:
    markdown_path: Path
    media_dir: Path


Runner = Callable[[list[str]], None]


def convert_word_to_markdown(
    options: WordToMarkdownOptions,
    *,
    runner: Runner | None = None,
) -> WordToMarkdownResult:
    input_path = options.input_path
    _validate_input(input_path)

    markdown_path, media_dir, extract_dir = _resolve_paths(options)
    if markdown_path.exists() and not options.overwrite:
        raise OutputExistsError(f"Output already exists: {markdown_path}")

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "pandoc",
        str(input_path),
        "--from",
        "docx",
        "--to",
        "gfm+tex_math_dollars",
        "--extract-media",
        str(extract_dir),
        "-o",
        str(markdown_path),
    ]

    try:
        (runner or _run_pandoc)(command)
    except FileNotFoundError as exc:
        raise PandocNotFoundError("Pandoc executable not found on PATH.") from exc
    except CalledProcessError as exc:
        message = exc.stderr or str(exc)
        raise PandocConversionError(f"Pandoc conversion failed: {message}") from exc

    return WordToMarkdownResult(markdown_path=markdown_path, media_dir=media_dir)


def _run_pandoc(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True, text=True)


def _validate_input(input_path: Path) -> None:
    if not input_path.is_file():
        raise InputDocumentError(f"Input document not found: {input_path}")
    if input_path.suffix.lower() != ".docx":
        raise InputDocumentError(f"Input document must be a .docx file: {input_path}")


def _resolve_paths(options: WordToMarkdownOptions) -> tuple[Path, Path, Path]:
    if options.output is not None:
        markdown_path = options.output
        media_dir = markdown_path.parent / "media"
        return markdown_path, media_dir, markdown_path.parent

    article_dir = options.output_dir / options.input_path.stem
    markdown_path = article_dir / f"{options.input_path.stem}.md"
    media_dir = article_dir / "media"
    return markdown_path, media_dir, article_dir
