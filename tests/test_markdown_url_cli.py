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


def test_cli_returns_nonzero_for_archive_errors(capsys: pytest.CaptureFixture[str]) -> None:
    def archive(url: str, options: ArchiveOptions) -> ArchiveResult:
        raise ArchiveError("Could not extract article content")

    exit_code = main(["https://example.com/article"], archive=archive)

    assert exit_code == 1
    assert "Error: Could not extract article content" in capsys.readouterr().err
