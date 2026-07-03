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
            "markdown+tex_math_dollars",
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


def test_convert_normalizes_extracted_media_links_and_reports_warning(tmp_path: Path) -> None:
    input_path = tmp_path / "Report.docx"
    save_docx(input_path)

    def runner(command: list[str]) -> None:
        output_path = Path(command[-1])
        extract_dir = Path(command[command.index("--extract-media") + 1])
        media_dir = extract_dir / "media"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        media_dir.mkdir(parents=True, exist_ok=True)
        (media_dir / "image1.emf").write_bytes(b"image")
        output_path.write_text(
            f'$$![]({extract_dir}\\media/image1.emf)',
            encoding="utf-8",
        )

    result = convert_word_to_markdown(
        WordToMarkdownOptions(input_path=input_path, output_dir=tmp_path / "exports"),
        runner=runner,
    )

    assert result.markdown_path.read_text(encoding="utf-8") == "![](./media/image1.emf)"
    assert result.warnings == (
        "1 media file(s) were extracted and kept as images; image-based formulas "
        "are not converted to LaTeX.",
    )


def test_convert_replaces_formula_images_with_latex_when_ocr_enabled(tmp_path: Path) -> None:
    input_path = tmp_path / "Report.docx"
    save_docx(input_path)

    def runner(command: list[str]) -> None:
        output_path = Path(command[-1])
        extract_dir = Path(command[command.index("--extract-media") + 1])
        media_dir = extract_dir / "media"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        media_dir.mkdir(parents=True, exist_ok=True)
        (media_dir / "image1.emf").write_bytes(b"image")
        (media_dir / "image2.emf").write_bytes(b"image")
        output_path.write_text(
            "\n".join(
                [
                    f"![]({extract_dir}/media/image1.emf){{width=\"6.5in\"}}",
                    f"inline ![]({extract_dir}/media/image2.emf) text",
                ]
            ),
            encoding="utf-8",
        )

    ocr_calls: list[list[Path]] = []

    def formula_image_ocr(image_paths: list[Path]) -> dict[Path, str]:
        ocr_calls.append(image_paths)
        return {
            image_paths[0]: r"k_{m i}=Z_{L K i}\cdot k_{S i}",
            image_paths[1]: r"e x p(x)+\\l n(y)",
        }

    result = convert_word_to_markdown(
        WordToMarkdownOptions(input_path=input_path, output_dir=tmp_path / "exports"),
        runner=runner,
        formula_image_ocr=formula_image_ocr,
    )

    assert ocr_calls == [
        [
            tmp_path / "exports" / "Report" / "media" / "image1.emf",
            tmp_path / "exports" / "Report" / "media" / "image2.emf",
        ]
    ]
    assert result.markdown_path.read_text(encoding="utf-8") == "\n".join(
        [
            r"$$k_{mi}=Z_{LKi}\cdot k_{Si}$$",
            r"inline $\exp(x)+\ln(y)$ text",
        ]
    )
    assert result.warnings == ()


def test_convert_keeps_formula_images_when_ocr_has_no_result(tmp_path: Path) -> None:
    input_path = tmp_path / "Report.docx"
    save_docx(input_path)

    def runner(command: list[str]) -> None:
        output_path = Path(command[-1])
        extract_dir = Path(command[command.index("--extract-media") + 1])
        media_dir = extract_dir / "media"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        media_dir.mkdir(parents=True, exist_ok=True)
        (media_dir / "image1.emf").write_bytes(b"image")
        output_path.write_text(f"![]({extract_dir}/media/image1.emf)", encoding="utf-8")

    result = convert_word_to_markdown(
        WordToMarkdownOptions(input_path=input_path, output_dir=tmp_path / "exports"),
        runner=runner,
        formula_image_ocr=lambda image_paths: {},
    )

    assert result.markdown_path.read_text(encoding="utf-8") == "![](./media/image1.emf)"
    assert result.warnings == (
        "1 media file(s) were extracted and kept as images; image-based formulas "
        "are not converted to LaTeX.",
    )


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


def test_cli_accepts_formula_ocr_python_option(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    input_path = tmp_path / "source.docx"
    ocr_python = tmp_path / "ocr-python.exe"
    save_docx(input_path)
    calls: list[WordToMarkdownOptions] = []

    def converter(options: WordToMarkdownOptions) -> WordToMarkdownResult:
        calls.append(options)
        return WordToMarkdownResult(
            markdown_path=tmp_path / "source.md",
            media_dir=tmp_path / "media",
        )

    exit_code = main(
        [
            str(input_path),
            "--formula-ocr-python",
            str(ocr_python),
            "--formula-ocr-device",
            "cpu",
        ],
        converter=converter,
    )

    assert exit_code == 0
    assert calls == [
        WordToMarkdownOptions(
            input_path=input_path,
            formula_ocr_python=ocr_python,
            formula_ocr_device="cpu",
        )
    ]


def test_cli_prints_conversion_warnings(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    input_path = tmp_path / "source.docx"
    output_path = tmp_path / "source.md"
    save_docx(input_path)

    def converter(options: WordToMarkdownOptions) -> WordToMarkdownResult:
        return WordToMarkdownResult(
            markdown_path=output_path,
            media_dir=tmp_path / "media",
            warnings=("2 media file(s) were extracted and kept as images.",),
        )

    exit_code = main([str(input_path)], converter=converter)

    assert exit_code == 0
    output = capsys.readouterr()
    assert "Warning: 2 media file(s) were extracted and kept as images." in output.err


def test_cli_returns_nonzero_for_conversion_errors(capsys: pytest.CaptureFixture[str]) -> None:
    def converter(options: WordToMarkdownOptions) -> WordToMarkdownResult:
        raise WordToMarkdownError("Could not convert document")

    exit_code = main(["input.docx"], converter=converter)

    assert exit_code == 1
    assert "Error: Could not convert document" in capsys.readouterr().err
