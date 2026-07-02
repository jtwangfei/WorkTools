# Word to Markdown Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tested CLI that converts `.docx` files to Markdown with Pandoc, preserving common Word structure and LaTeX math where Pandoc supports it.

**Architecture:** Keep conversion behavior in `src/worktools/word_to_markdown.py` and keep the CLI in `src/worktools/word_to_markdown_cli.py`. Inject the subprocess runner in tests so unit tests do not require Pandoc to be installed.

**Tech Stack:** Python 3.10, `argparse`, `subprocess`, `pytest`, external `pandoc` executable.

---

## Improvements To Apply

- Use an injectable runner for Pandoc so tests verify command construction without depending on local Pandoc installation.
- Keep output rules deterministic: default output goes to `exports/markdown/<stem>/<stem>.md`; explicit output writes media beside the chosen `.md` in `media/`.
- Do not add Python dependencies. Pandoc is an external system requirement documented in README.

## File Structure

- Create `src/worktools/word_to_markdown.py`: options/result dataclasses, validation, output path resolution, Pandoc command construction, error mapping.
- Create `src/worktools/word_to_markdown_cli.py`: thin `argparse` wrapper and CLI output.
- Create `tests/test_word_to_markdown.py`: core and CLI tests.
- Modify `README.md`: document the new command and Pandoc requirement.

## Task 1: Core Converter

**Files:**
- Create: `src/worktools/word_to_markdown.py`
- Create: `tests/test_word_to_markdown.py`

- [ ] **Step 1: Write failing core tests**

Create `tests/test_word_to_markdown.py` with tests for default paths, explicit output, validation, overwrite behavior, and Pandoc error mapping.

```python
from pathlib import Path
from subprocess import CalledProcessError

import pytest

from worktools.word_to_markdown import (
    InputDocumentError,
    OutputExistsError,
    PandocConversionError,
    PandocNotFoundError,
    WordToMarkdownOptions,
    convert_word_to_markdown,
)


def save_docx(path: Path) -> None:
    path.write_bytes(b"docx")


def test_convert_uses_default_output_paths_and_pandoc_options(tmp_path: Path) -> None:
    input_path = tmp_path / "Report.docx"
    save_docx(input_path)
    calls: list[list[str]] = []

    def runner(command: list[str]) -> None:
        calls.append(command)

    result = convert_word_to_markdown(
        WordToMarkdownOptions(input_path=input_path, output_dir=tmp_path / "exports"),
        runner=runner,
    )

    assert result.markdown_path == tmp_path / "exports" / "Report" / "Report.md"
    assert result.media_dir == tmp_path / "exports" / "Report" / "media"
    assert calls == [
        [
            "pandoc",
            str(input_path),
            "--from",
            "docx",
            "--to",
            "gfm+tex_math_dollars",
            "--extract-media",
            str(tmp_path / "exports" / "Report"),
            "-o",
            str(tmp_path / "exports" / "Report" / "Report.md"),
        ]
    ]


def test_convert_uses_explicit_output_path(tmp_path: Path) -> None:
    input_path = tmp_path / "source.docx"
    output_path = tmp_path / "notes" / "source.md"
    save_docx(input_path)

    result = convert_word_to_markdown(
        WordToMarkdownOptions(input_path=input_path, output=output_path),
        runner=lambda command: None,
    )

    assert result.markdown_path == output_path
    assert result.media_dir == tmp_path / "notes" / "media"


def test_convert_rejects_missing_input(tmp_path: Path) -> None:
    with pytest.raises(InputDocumentError):
        convert_word_to_markdown(
            WordToMarkdownOptions(input_path=tmp_path / "missing.docx"),
            runner=lambda command: None,
        )


def test_convert_rejects_non_docx_input(tmp_path: Path) -> None:
    input_path = tmp_path / "notes.txt"
    input_path.write_text("body", encoding="utf-8")

    with pytest.raises(InputDocumentError):
        convert_word_to_markdown(
            WordToMarkdownOptions(input_path=input_path),
            runner=lambda command: None,
        )


def test_convert_rejects_existing_output_without_overwrite(tmp_path: Path) -> None:
    input_path = tmp_path / "source.docx"
    output_path = tmp_path / "source.md"
    save_docx(input_path)
    output_path.write_text("existing", encoding="utf-8")

    with pytest.raises(OutputExistsError):
        convert_word_to_markdown(
            WordToMarkdownOptions(input_path=input_path, output=output_path),
            runner=lambda command: None,
        )


def test_convert_allows_existing_output_with_overwrite(tmp_path: Path) -> None:
    input_path = tmp_path / "source.docx"
    output_path = tmp_path / "source.md"
    save_docx(input_path)
    output_path.write_text("existing", encoding="utf-8")

    result = convert_word_to_markdown(
        WordToMarkdownOptions(input_path=input_path, output=output_path, overwrite=True),
        runner=lambda command: None,
    )

    assert result.markdown_path == output_path


def test_convert_reports_missing_pandoc(tmp_path: Path) -> None:
    input_path = tmp_path / "source.docx"
    save_docx(input_path)

    def runner(command: list[str]) -> None:
        raise FileNotFoundError("pandoc")

    with pytest.raises(PandocNotFoundError):
        convert_word_to_markdown(WordToMarkdownOptions(input_path=input_path), runner=runner)


def test_convert_reports_pandoc_failure(tmp_path: Path) -> None:
    input_path = tmp_path / "source.docx"
    save_docx(input_path)

    def runner(command: list[str]) -> None:
        raise CalledProcessError(2, command, stderr="bad input")

    with pytest.raises(PandocConversionError, match="bad input"):
        convert_word_to_markdown(WordToMarkdownOptions(input_path=input_path), runner=runner)
```

- [ ] **Step 2: Run core tests to verify they fail**

Run: `python -m pytest tests/test_word_to_markdown.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'worktools.word_to_markdown'`.

- [ ] **Step 3: Implement minimal core converter**

Create `src/worktools/word_to_markdown.py` with dataclasses, errors, path resolution, command construction, and subprocess execution.

- [ ] **Step 4: Run core tests to verify they pass**

Run: `python -m pytest tests/test_word_to_markdown.py -q`

Expected: all tests in `tests/test_word_to_markdown.py` pass.

## Task 2: CLI Wrapper

**Files:**
- Modify: `tests/test_word_to_markdown.py`
- Create: `src/worktools/word_to_markdown_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Append tests that inject a fake converter into the CLI.

```python
from worktools.word_to_markdown import WordToMarkdownError, WordToMarkdownResult
from worktools.word_to_markdown_cli import main


def test_cli_calls_converter_with_expected_options(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    input_path = tmp_path / "source.docx"
    output_path = tmp_path / "source.md"
    save_docx(input_path)
    calls: list[WordToMarkdownOptions] = []

    def converter(options: WordToMarkdownOptions) -> WordToMarkdownResult:
        calls.append(options)
        return WordToMarkdownResult(markdown_path=output_path, media_dir=tmp_path / "media")

    exit_code = main(
        [str(input_path), "-o", str(output_path), "--overwrite"],
        converter=converter,
    )

    assert exit_code == 0
    assert calls == [WordToMarkdownOptions(input_path=input_path, output=output_path, overwrite=True)]
    output = capsys.readouterr()
    assert f"Saved Markdown: {output_path}" in output.out
    assert f"Saved media: {tmp_path / 'media'}" in output.out


def test_cli_returns_nonzero_for_conversion_errors(capsys: pytest.CaptureFixture[str]) -> None:
    def converter(options: WordToMarkdownOptions) -> WordToMarkdownResult:
        raise WordToMarkdownError("Could not convert document")

    exit_code = main(["input.docx"], converter=converter)

    assert exit_code == 1
    assert "Error: Could not convert document" in capsys.readouterr().err
```

- [ ] **Step 2: Run CLI tests to verify they fail**

Run: `python -m pytest tests/test_word_to_markdown.py::test_cli_calls_converter_with_expected_options tests/test_word_to_markdown.py::test_cli_returns_nonzero_for_conversion_errors -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'worktools.word_to_markdown_cli'`.

- [ ] **Step 3: Implement minimal CLI wrapper**

Create `src/worktools/word_to_markdown_cli.py` with `argparse`, dependency injection for tests, and stderr error handling.

- [ ] **Step 4: Run CLI tests to verify they pass**

Run: `python -m pytest tests/test_word_to_markdown.py -q`

Expected: all Word to Markdown tests pass.

## Task 3: Documentation And Full Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

Add a `Word to Markdown Tool` section after the `Markdown URL Tool` section with:

~~~markdown
## Word to Markdown Tool

Convert a Word `.docx` file into Markdown using Pandoc:

```powershell
python -m worktools.word_to_markdown_cli D:\Docs\report.docx
```

By default, output is written under `exports/markdown/`:

```text
exports/markdown/
  report/
    report.md
    media/
      image1.png
```

Use a custom Markdown output path:

```powershell
python -m worktools.word_to_markdown_cli D:\Docs\report.docx -o D:\Notes\report.md
```

Useful options:

- `--overwrite`: replace an existing Markdown output file.

This tool requires the `pandoc` executable on `PATH`. Pandoc handles Word structure conversion and emits Word formulas as LaTeX math where supported.
~~~

- [ ] **Step 2: Run full tests**

Run: `python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 3: Run lint**

Run: `python -m ruff check .`

Expected: no lint errors.
