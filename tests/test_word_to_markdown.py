from pathlib import Path
from subprocess import CalledProcessError

import pytest

from worktools.word_to_markdown import (
    InputDocumentError,
    OutputExistsError,
    PandocConversionError,
    PandocNotFoundError,
    WordToMarkdownError,
    WordToMarkdownOptions,
    WordToMarkdownResult,
    convert_word_to_markdown,
)
from worktools.word_to_markdown_cli import main


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
    assert calls == [
        WordToMarkdownOptions(input_path=input_path, output=output_path, overwrite=True)
    ]
    output = capsys.readouterr()
    assert f"Saved Markdown: {output_path}" in output.out
    assert f"Saved media: {tmp_path / 'media'}" in output.out


def test_cli_returns_nonzero_for_conversion_errors(capsys: pytest.CaptureFixture[str]) -> None:
    def converter(options: WordToMarkdownOptions) -> WordToMarkdownResult:
        raise WordToMarkdownError("Could not convert document")

    exit_code = main(["input.docx"], converter=converter)

    assert exit_code == 1
    assert "Error: Could not convert document" in capsys.readouterr().err
