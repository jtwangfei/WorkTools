from pathlib import Path

import pytest

from worktools.web_to_markdown import (
    ArchiveOptions,
    OutputExistsError,
    archive_url,
    build_archive_paths,
    sanitize_filename,
)


def test_sanitize_filename_removes_invalid_characters() -> None:
    assert sanitize_filename(" My: Article / Title? Name! ") == "my-article-title-name"


def test_build_archive_paths_uses_article_folder() -> None:
    paths = build_archive_paths(Path("exports/markdown"), "My Article", "https://example.com/a")

    assert paths.article_dir == Path("exports/markdown/my-article")
    assert paths.markdown_path == Path("exports/markdown/my-article/my-article.md")
    assert paths.images_dir == Path("exports/markdown/my-article/images")


def test_archive_url_writes_markdown_and_downloads_body_images(tmp_path: Path) -> None:
    def fetch_html(url: str, timeout: int) -> str:
        assert url == "https://example.com/articles/post"
        assert timeout == 20
        return "<html><title>Ignored fallback</title></html>"

    def extract_html(html: str, url: str) -> tuple[str, str]:
        assert url == "https://example.com/articles/post"
        return (
            "Useful Article",
            """
            <article>
              <h1>Useful Article</h1>
              <p>Read the <a href="https://example.com/more">details</a>.</p>
              <img src="/images/photo.jpg" alt="Photo">
            </article>
            """,
        )

    downloaded: list[tuple[str, Path]] = []

    def download_image(url: str, destination: Path, timeout: int) -> None:
        downloaded.append((url, destination))
        destination.write_bytes(b"image")

    result = archive_url(
        "https://example.com/articles/post",
        ArchiveOptions(output_dir=tmp_path),
        fetch_html=fetch_html,
        extract_html=extract_html,
        download_image=download_image,
    )

    assert result.markdown_path == tmp_path / "useful-article" / "useful-article.md"
    assert result.images_dir == tmp_path / "useful-article" / "images"
    assert downloaded == [
        (
            "https://example.com/images/photo.jpg",
            tmp_path / "useful-article" / "images" / "image-001.jpg",
        )
    ]
    assert result.markdown_path.read_text(encoding="utf-8").strip() == (
        "# Useful Article\n\n"
        "Read the details.\n\n"
        "![Photo](images/image-001.jpg)"
    )


def test_archive_url_can_keep_links_when_requested(tmp_path: Path) -> None:
    def fetch_html(url: str, timeout: int) -> str:
        return "<html></html>"

    def extract_html(html: str, url: str) -> tuple[str, str]:
        return ("Linked Article", '<p>Open <a href="https://example.com">source</a>.</p>')

    result = archive_url(
        "https://example.com/article",
        ArchiveOptions(output_dir=tmp_path, keep_links=True),
        fetch_html=fetch_html,
        extract_html=extract_html,
    )

    assert result.markdown_path.read_text(encoding="utf-8").strip() == (
        "Open [source](https://example.com)."
    )


def test_archive_url_refuses_existing_folder_without_overwrite(tmp_path: Path) -> None:
    article_dir = tmp_path / "existing-title"
    article_dir.mkdir()

    def fetch_html(url: str, timeout: int) -> str:
        return "<html></html>"

    def extract_html(html: str, url: str) -> tuple[str, str]:
        return ("Existing Title", "<p>Body</p>")

    with pytest.raises(OutputExistsError):
        archive_url(
            "https://example.com/article",
            ArchiveOptions(output_dir=tmp_path),
            fetch_html=fetch_html,
            extract_html=extract_html,
        )


def test_archive_url_overwrites_existing_folder_when_requested(tmp_path: Path) -> None:
    article_dir = tmp_path / "existing-title"
    article_dir.mkdir()
    (article_dir / "old.md").write_text("old", encoding="utf-8")

    def fetch_html(url: str, timeout: int) -> str:
        return "<html></html>"

    def extract_html(html: str, url: str) -> tuple[str, str]:
        return ("Existing Title", "<p>New body</p>")

    result = archive_url(
        "https://example.com/article",
        ArchiveOptions(output_dir=tmp_path, overwrite=True),
        fetch_html=fetch_html,
        extract_html=extract_html,
    )

    assert not (article_dir / "old.md").exists()
    assert result.markdown_path.read_text(encoding="utf-8").strip() == "New body"
