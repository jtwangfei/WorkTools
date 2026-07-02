# Word Merge Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested command-line tool that merges one or more `.docx` files into a selected Word template at a `{{content}}` placeholder.

**Architecture:** Keep the command wrapper thin and put behavior in `src/worktools/word_merge.py`. Use `python-docx` to read templates and inputs, validate the placeholder contract, insert paragraph text in command-line order, and save the output. The first version deliberately converts source paragraphs into new paragraphs using the template placeholder style instead of copying complex Word objects.

**Tech Stack:** Python 3.10, `python-docx`, `argparse`, `pytest`.

---

### Task 1: Add Word Merge Tests

**Files:**
- Create: `tests/test_word_merge.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_word_merge.py` with tests that generate temporary `.docx` files using `python-docx`:

```python
from pathlib import Path

import pytest
from docx import Document

from worktools.word_merge import (
    DuplicatePlaceholderError,
    InputDocumentError,
    MergeModeNotImplementedError,
    MissingPlaceholderError,
    OutputExistsError,
    TemplatePlaceholderError,
    WordMergeOptions,
    merge_documents,
    resolve_template_path,
)


def save_docx(path: Path, paragraphs: list[str], style: str | None = None) -> None:
    document = Document()
    for text in paragraphs:
        paragraph = document.add_paragraph(text)
        if style:
            paragraph.style = style
    document.save(path)


def save_template(path: Path, placeholder: str = "{{content}}", style: str = "Quote") -> None:
    document = Document()
    document.add_paragraph("Header")
    paragraph = document.add_paragraph(placeholder)
    paragraph.style = style
    document.add_paragraph("Footer")
    document.save(path)


def read_paragraphs(path: Path) -> list[str]:
    return [paragraph.text for paragraph in Document(path).paragraphs]


def test_resolve_template_path_uses_existing_file(tmp_path: Path) -> None:
    template = tmp_path / "custom.docx"
    save_template(template)

    assert resolve_template_path(str(template), tmp_path) == template


def test_resolve_template_path_uses_named_template(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    template = templates_dir / "report.docx"
    save_template(template)

    assert resolve_template_path("report", tmp_path) == template


def test_merge_documents_inserts_inputs_in_order_and_uses_template_style(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    template = templates_dir / "report.docx"
    first = tmp_path / "first.docx"
    second = tmp_path / "second.docx"
    output = tmp_path / "merged.docx"

    save_template(template, style="Quote")
    save_docx(first, ["First A", "First B"])
    save_docx(second, ["Second A"])

    merge_documents(
        WordMergeOptions(
            template="report",
            inputs=[first, second],
            output=output,
            base_dir=tmp_path,
        )
    )

    document = Document(output)
    assert [paragraph.text for paragraph in document.paragraphs] == [
        "Header",
        "First A",
        "First B",
        "Second A",
        "Footer",
    ]
    assert [paragraph.style.name for paragraph in document.paragraphs[1:4]] == [
        "Quote",
        "Quote",
        "Quote",
    ]


def test_merge_documents_rejects_missing_placeholder(tmp_path: Path) -> None:
    template = tmp_path / "template.docx"
    input_doc = tmp_path / "input.docx"
    document = Document()
    document.add_paragraph("No marker")
    document.save(template)
    save_docx(input_doc, ["Body"])

    with pytest.raises(MissingPlaceholderError):
        merge_documents(
            WordMergeOptions(template=str(template), inputs=[input_doc], output=tmp_path / "out.docx")
        )


def test_merge_documents_rejects_duplicate_placeholders(tmp_path: Path) -> None:
    template = tmp_path / "template.docx"
    input_doc = tmp_path / "input.docx"
    document = Document()
    document.add_paragraph("{{content}}")
    document.add_paragraph("{{content}}")
    document.save(template)
    save_docx(input_doc, ["Body"])

    with pytest.raises(DuplicatePlaceholderError):
        merge_documents(
            WordMergeOptions(template=str(template), inputs=[input_doc], output=tmp_path / "out.docx")
        )


def test_merge_documents_rejects_placeholder_with_other_text(tmp_path: Path) -> None:
    template = tmp_path / "template.docx"
    input_doc = tmp_path / "input.docx"
    save_template(template, placeholder="Before {{content}}")
    save_docx(input_doc, ["Body"])

    with pytest.raises(TemplatePlaceholderError):
        merge_documents(
            WordMergeOptions(template=str(template), inputs=[input_doc], output=tmp_path / "out.docx")
        )


def test_merge_documents_rejects_non_docx_input(tmp_path: Path) -> None:
    template = tmp_path / "template.docx"
    input_doc = tmp_path / "input.txt"
    save_template(template)
    input_doc.write_text("Body", encoding="utf-8")

    with pytest.raises(InputDocumentError):
        merge_documents(
            WordMergeOptions(template=str(template), inputs=[input_doc], output=tmp_path / "out.docx")
        )


def test_merge_documents_rejects_existing_output_without_overwrite(tmp_path: Path) -> None:
    template = tmp_path / "template.docx"
    input_doc = tmp_path / "input.docx"
    output = tmp_path / "out.docx"
    save_template(template)
    save_docx(input_doc, ["Body"])
    save_docx(output, ["Existing"])

    with pytest.raises(OutputExistsError):
        merge_documents(WordMergeOptions(template=str(template), inputs=[input_doc], output=output))


def test_merge_documents_rejects_summarize_mode(tmp_path: Path) -> None:
    template = tmp_path / "template.docx"
    input_doc = tmp_path / "input.docx"
    save_template(template)
    save_docx(input_doc, ["Body"])

    with pytest.raises(MergeModeNotImplementedError):
        merge_documents(
            WordMergeOptions(
                template=str(template),
                inputs=[input_doc],
                output=tmp_path / "out.docx",
                mode="summarize",
            )
        )
```

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests/test_word_merge.py -q`

Expected: collection or import failure because `worktools.word_merge` does not exist yet.

### Task 2: Implement Core Merge Module

**Files:**
- Create: `src/worktools/word_merge.py`
- Modify: `pyproject.toml`
- Modify: `requirements.txt`

- [ ] **Step 1: Add dependency**

Add `python-docx>=1.1` to `[project].dependencies` in `pyproject.toml` and to `requirements.txt`.

- [ ] **Step 2: Write minimal implementation**

Create `src/worktools/word_merge.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from docx import Document
from docx.document import Document as DocxDocument
from docx.text.paragraph import Paragraph

PLACEHOLDER = "{{content}}"
MergeMode = Literal["direct", "summarize"]


class WordMergeError(Exception):
    """Base error for Word merge failures."""


class TemplateNotFoundError(WordMergeError):
    """Raised when a template cannot be resolved."""


class MissingPlaceholderError(WordMergeError):
    """Raised when the template does not contain the content placeholder."""


class DuplicatePlaceholderError(WordMergeError):
    """Raised when the template contains more than one content placeholder."""


class TemplatePlaceholderError(WordMergeError):
    """Raised when the placeholder paragraph violates the template contract."""


class InputDocumentError(WordMergeError):
    """Raised when an input document is invalid."""


class OutputExistsError(WordMergeError):
    """Raised when the output already exists and overwrite is disabled."""


class MergeModeNotImplementedError(WordMergeError):
    """Raised when a reserved merge mode is requested."""


@dataclass(frozen=True)
class WordMergeOptions:
    template: str
    inputs: list[Path]
    output: Path
    mode: MergeMode = "direct"
    overwrite: bool = False
    base_dir: Path = field(default_factory=Path.cwd)


@dataclass(frozen=True)
class WordMergeResult:
    output: Path


def resolve_template_path(template: str, base_dir: Path | None = None) -> Path:
    base = base_dir or Path.cwd()
    direct_path = Path(template)
    if direct_path.is_file():
        return direct_path

    for suffix in (".docx", ".dotx"):
        candidate = base / "templates" / f"{template}{suffix}"
        if candidate.is_file():
            return candidate

    raise TemplateNotFoundError(f"Template not found: {template}")


def merge_documents(options: WordMergeOptions) -> WordMergeResult:
    if options.mode == "summarize":
        raise MergeModeNotImplementedError("Summarize mode is reserved but not implemented.")
    if options.mode != "direct":
        raise WordMergeError(f"Unsupported merge mode: {options.mode}")
    if options.output.exists() and not options.overwrite:
        raise OutputExistsError(f"Output already exists: {options.output}")

    template_path = resolve_template_path(options.template, options.base_dir)
    _validate_inputs(options.inputs)

    document = Document(template_path)
    placeholder = _find_placeholder(document)
    style_name = placeholder.style.name
    insert_after = placeholder._p
    _remove_paragraph(placeholder)

    for input_path in options.inputs:
        source = Document(input_path)
        for source_paragraph in source.paragraphs:
            if not source_paragraph.text:
                continue
            insert_after = _insert_paragraph_after(document, insert_after, source_paragraph.text, style_name)

    options.output.parent.mkdir(parents=True, exist_ok=True)
    document.save(options.output)
    return WordMergeResult(output=options.output)


def _validate_inputs(inputs: list[Path]) -> None:
    if not inputs:
        raise InputDocumentError("At least one input document is required.")
    for input_path in inputs:
        if not input_path.is_file():
            raise InputDocumentError(f"Input document not found: {input_path}")
        if input_path.suffix.lower() != ".docx":
            raise InputDocumentError(f"Input document must be a .docx file: {input_path}")


def _find_placeholder(document: DocxDocument) -> Paragraph:
    matches = [paragraph for paragraph in document.paragraphs if PLACEHOLDER in paragraph.text]
    if not matches:
        raise MissingPlaceholderError(f"Template must contain {PLACEHOLDER}.")
    if len(matches) > 1:
        raise DuplicatePlaceholderError(f"Template must contain only one {PLACEHOLDER}.")

    placeholder = matches[0]
    if placeholder.text.strip() != PLACEHOLDER:
        raise TemplatePlaceholderError(f"{PLACEHOLDER} must be the only text in its paragraph.")
    return placeholder


def _remove_paragraph(paragraph: Paragraph) -> None:
    element = paragraph._element
    element.getparent().remove(element)
    paragraph._p = paragraph._element = None


def _insert_paragraph_after(
    document: DocxDocument,
    previous_element,
    text: str,
    style_name: str,
):
    paragraph = document.add_paragraph()
    paragraph.text = text
    paragraph.style = style_name
    previous_element.addnext(paragraph._p)
    return paragraph._p
```

- [ ] **Step 3: Run tests to verify GREEN**

Run: `python -m pytest tests/test_word_merge.py -q`

Expected: all tests pass.

### Task 3: Add Thin CLI Wrapper

**Files:**
- Create: `src/worktools/word_merge_cli.py`
- Modify: `tests/test_word_merge.py`

- [ ] **Step 1: Add failing CLI parser test**

Append to `tests/test_word_merge.py`:

```python
from worktools.word_merge_cli import build_parser


def test_cli_parser_builds_word_merge_options() -> None:
    parser = build_parser()

    args = parser.parse_args(
        ["--template", "report", "a.docx", "b.docx", "-o", "merged.docx", "--overwrite"]
    )

    assert args.template == "report"
    assert args.inputs == ["a.docx", "b.docx"]
    assert args.output == "merged.docx"
    assert args.mode == "direct"
    assert args.overwrite is True
```

- [ ] **Step 2: Run CLI parser test to verify RED**

Run: `python -m pytest tests/test_word_merge.py::test_cli_parser_builds_word_merge_options -q`

Expected: import failure because `worktools.word_merge_cli` does not exist yet.

- [ ] **Step 3: Implement CLI wrapper**

Create `src/worktools/word_merge_cli.py` with:

```python
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
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `python -m pytest tests/test_word_merge.py -q`

Expected: all tests pass.

### Task 4: Final Verification

**Files:**
- No source changes expected.

- [ ] **Step 1: Run focused tests**

Run: `python -m pytest tests/test_word_merge.py -q`

Expected: all Word merge tests pass.

- [ ] **Step 2: Run all tests**

Run: `python -m pytest -q`

Expected: all repository tests pass.

- [ ] **Step 3: Check working tree**

Run: `git status --short`

Expected: only files changed by this feature are listed, plus any unrelated pre-existing files.
