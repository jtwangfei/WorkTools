from pathlib import Path

import pytest

from worktools.markdown_url import main
from worktools.web_to_markdown import ArchiveError, ArchiveOptions, ArchiveResult


def test_cli_calls_archive_with_expected_options(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    calls: list[tuple[str, ArchiveOptions]] = []

    def archive(url: str, options: ArchiveOptions) -> ArchiveResult:
        calls.append((url, options))
        return ArchiveResult(
            url=url,
            title="Example",
            markdown_path=tmp_path / "example" / "example.md",
            article_dir=tmp_path / "example",
            images_dir=tmp_path / "example" / "images",
            warnings=("Skipped image https://example.com/a.png: timeout",),
        )

    exit_code = main(
        [
            "https://example.com/article",
            "--output-dir",
            str(tmp_path),
            "--overwrite",
            "--timeout",
            "7",
            "--keep-links",
        ],
        archive=archive,
    )

    assert exit_code == 0
    assert calls == [
        (
            "https://example.com/article",
            ArchiveOptions(output_dir=tmp_path, overwrite=True, timeout=7, keep_links=True),
        )
    ]
    output = capsys.readouterr()
    assert f"Saved Markdown: {tmp_path / 'example' / 'example.md'}" in output.out
    assert "Warning: Skipped image https://example.com/a.png: timeout" in output.err


def test_cli_can_archive_saved_html_file(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    html_path = tmp_path / "article.html"
    html_path.write_text("<html></html>", encoding="utf-8")
    calls: list[tuple[Path, ArchiveOptions, str | None]] = []

    def archive_html_file(
        html_file: Path, options: ArchiveOptions, source_url: str | None = None
    ) -> ArchiveResult:
        calls.append((html_file, options, source_url))
        return ArchiveResult(
            url=source_url or html_file.as_uri(),
            title="Saved",
            markdown_path=tmp_path / "saved" / "saved.md",
            article_dir=tmp_path / "saved",
            images_dir=tmp_path / "saved" / "images",
        )

    exit_code = main(
        [
            "--html-file",
            str(html_path),
            "--source-url",
            "https://zhuanlan.zhihu.com/p/2049609181892711018",
            "--output-dir",
            str(tmp_path),
        ],
        archive_html_file=archive_html_file,
    )

    assert exit_code == 0
    assert calls == [
        (
            html_path,
            ArchiveOptions(output_dir=tmp_path, overwrite=False, timeout=20, keep_links=False),
            "https://zhuanlan.zhihu.com/p/2049609181892711018",
        )
    ]
    assert f"Saved Markdown: {tmp_path / 'saved' / 'saved.md'}" in capsys.readouterr().out


def test_cli_returns_nonzero_for_archive_errors(capsys: pytest.CaptureFixture[str]) -> None:
    def archive(url: str, options: ArchiveOptions) -> ArchiveResult:
        raise ArchiveError("Could not extract article content")

    exit_code = main(["https://example.com/article"], archive=archive)

    assert exit_code == 1
    assert "Error: Could not extract article content" in capsys.readouterr().err
