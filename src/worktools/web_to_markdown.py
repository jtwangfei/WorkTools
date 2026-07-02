"""Archive article URLs as Markdown plus local image assets."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from shutil import rmtree
from time import strftime
from urllib.parse import urljoin, urlparse
from urllib.request import url2pathname


class ArchiveError(RuntimeError):
    """Base error for article archiving failures."""


class FetchError(ArchiveError):
    """Raised when a URL cannot be fetched."""


class ExtractionError(ArchiveError):
    """Raised when article content cannot be extracted."""


class OutputExistsError(ArchiveError):
    """Raised when an output folder already exists and overwrite is disabled."""


@dataclass(frozen=True)
class ArchiveOptions:
    """Options controlling URL archive behavior."""

    output_dir: Path = Path("exports/markdown")
    overwrite: bool = False
    timeout: int = 20
    keep_links: bool = False


@dataclass(frozen=True)
class ArchivePaths:
    """Filesystem paths for one archived article."""

    slug: str
    article_dir: Path
    markdown_path: Path
    images_dir: Path


@dataclass(frozen=True)
class ArchiveResult:
    """Result of archiving one URL."""

    url: str
    title: str
    markdown_path: Path
    article_dir: Path
    images_dir: Path
    warnings: tuple[str, ...] = field(default_factory=tuple)


FetchHtml = Callable[[str, int], str]
ExtractHtml = Callable[[str, str], tuple[str, str]]
DownloadImage = Callable[[str, Path, int], None]


def sanitize_filename(value: str, *, fallback: str = "article", max_length: int = 80) -> str:
    """Convert a title into a compact filesystem-safe slug."""

    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", value)
    cleaned = cleaned.strip().lower()
    cleaned = re.sub(r"[^\w.-]+", "-", cleaned, flags=re.UNICODE)
    cleaned = re.sub(r"[-_]{2,}", "-", cleaned).strip("-. _")
    if not cleaned:
        cleaned = fallback
    return cleaned[:max_length].rstrip("-. _") or fallback


def build_archive_paths(output_dir: Path, title: str, source_url: str) -> ArchivePaths:
    """Build the output paths for one archived article."""

    slug = sanitize_filename(title, fallback=_fallback_slug(source_url))
    article_dir = output_dir / slug
    return ArchivePaths(
        slug=slug,
        article_dir=article_dir,
        markdown_path=article_dir / f"{slug}.md",
        images_dir=article_dir / "images",
    )


def archive_url(
    url: str,
    options: ArchiveOptions | None = None,
    *,
    fetch_html: FetchHtml | None = None,
    extract_html: ExtractHtml | None = None,
    download_image: DownloadImage | None = None,
) -> ArchiveResult:
    """Archive a URL into a per-article Markdown folder."""

    selected_options = options or ArchiveOptions()
    fetch = fetch_html or default_fetch_html

    html = fetch(url, selected_options.timeout)
    return archive_html(
        html,
        url,
        selected_options,
        extract_html=extract_html,
        download_image=download_image,
    )


def archive_html_file(
    html_path: Path,
    options: ArchiveOptions | None = None,
    source_url: str | None = None,
    *,
    extract_html: ExtractHtml | None = None,
    download_image: DownloadImage | None = None,
) -> ArchiveResult:
    """Archive a saved HTML file into a per-article Markdown folder."""

    resolved_html_path = html_path.resolve()
    html = resolved_html_path.read_text(encoding="utf-8")
    base_url = source_url or resolved_html_path.as_uri()
    return archive_html(
        html,
        base_url,
        options,
        extract_html=extract_html,
        download_image=download_image,
    )


def archive_html(
    html: str,
    source_url: str,
    options: ArchiveOptions | None = None,
    *,
    extract_html: ExtractHtml | None = None,
    download_image: DownloadImage | None = None,
) -> ArchiveResult:
    """Archive an HTML document into a per-article Markdown folder."""

    selected_options = options or ArchiveOptions()
    extract = extract_html or default_extract_html
    image_downloader = download_image or default_download_image

    title, article_html = extract(html, source_url)
    if not article_html.strip():
        raise ExtractionError(f"Could not extract article content from {source_url}")

    paths = build_archive_paths(selected_options.output_dir, title, source_url)
    _prepare_output(paths, selected_options.overwrite)

    warnings: list[str] = []
    markdown = rewrite_html_for_markdown(
        article_html,
        source_url,
        paths.images_dir,
        image_downloader,
        selected_options.timeout,
        keep_links=selected_options.keep_links,
        warnings=warnings,
    )
    paths.markdown_path.write_text(markdown.strip() + "\n", encoding="utf-8")

    return ArchiveResult(
        url=source_url,
        title=title,
        markdown_path=paths.markdown_path,
        article_dir=paths.article_dir,
        images_dir=paths.images_dir,
        warnings=tuple(warnings),
    )


def rewrite_html_for_markdown(
    article_html: str,
    source_url: str,
    images_dir: Path,
    download_image: DownloadImage,
    timeout: int,
    *,
    keep_links: bool = False,
    warnings: list[str] | None = None,
) -> str:
    """Download article images, rewrite their links, and convert HTML to Markdown."""

    from bs4 import BeautifulSoup
    from markdownify import markdownify

    collected_warnings = warnings if warnings is not None else []
    soup = BeautifulSoup(article_html, "html.parser")
    images_dir.mkdir(parents=True, exist_ok=True)

    for index, image in enumerate(soup.find_all("img"), start=1):
        source = image.get("src") or image.get("data-src") or image.get("data-original")
        if not source:
            image.decompose()
            continue

        image_url = urljoin(source_url, source)
        extension = _image_extension(image_url)
        local_name = f"image-{index:03d}{extension}"
        destination = images_dir / local_name
        try:
            download_image(image_url, destination, timeout)
        except Exception as exc:  # noqa: BLE001 - keep article archiving resilient.
            collected_warnings.append(f"Skipped image {image_url}: {exc}")
            image.decompose()
            continue

        image["src"] = f"images/{local_name}"
        for attribute in ("srcset", "data-src", "data-original"):
            image.attrs.pop(attribute, None)

    if not keep_links:
        for link in soup.find_all("a"):
            link.unwrap()

    return markdownify(str(soup), heading_style="ATX", bullets="-")


def default_fetch_html(url: str, timeout: int) -> str:
    """Fetch a web page as text."""

    import requests

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "WorkTools/0.1 (+https://github.com/)"},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise FetchError(f"Could not fetch {url}: {exc}") from exc
    response.encoding = response.encoding or response.apparent_encoding
    return response.text


def default_extract_html(html: str, url: str) -> tuple[str, str]:
    """Extract the main article HTML and title using trafilatura."""

    zhihu_article = _extract_zhihu_article_html(html, url)
    if zhihu_article:
        return zhihu_article

    import trafilatura

    extracted = trafilatura.extract(
        html,
        url=url,
        output_format="html",
        include_images=True,
        include_links=True,
    )
    if not extracted:
        raise ExtractionError(f"Could not extract article content from {url}")

    metadata = trafilatura.extract_metadata(html)
    title = metadata.title if metadata and metadata.title else _title_from_html(html)
    return title or _fallback_slug(url), extracted


def default_download_image(url: str, destination: Path, timeout: int) -> None:
    """Download one image to a destination path."""

    import requests

    parsed = urlparse(url)
    if parsed.scheme in {"", "file"}:
        source_path = _path_from_file_url(url) if parsed.scheme == "file" else Path(url)
        destination.write_bytes(source_path.read_bytes())
        return

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "WorkTools/0.1 (+https://github.com/)"},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise FetchError(f"Could not fetch image {url}: {exc}") from exc
    destination.write_bytes(response.content)


def _prepare_output(paths: ArchivePaths, overwrite: bool) -> None:
    if paths.article_dir.exists():
        if not overwrite:
            raise OutputExistsError(f"Output folder already exists: {paths.article_dir}")
        rmtree(paths.article_dir)
    paths.images_dir.mkdir(parents=True, exist_ok=True)


def _fallback_slug(source_url: str) -> str:
    host = urlparse(source_url).netloc or "article"
    return sanitize_filename(f"{host}-{strftime('%Y%m%d-%H%M%S')}", fallback="article")


def _title_from_html(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title")
    return title.get_text(" ", strip=True) if title else ""


def _extract_zhihu_article_html(html: str, url: str) -> tuple[str, str] | None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one(".Post-RichTextContainer")
    if not container:
        return None
    body = container.select_one(".Post-RichText") or container

    title_node = soup.select_one(".Post-Title") or soup.find("h1")
    title = (
        title_node.get_text(" ", strip=True)
        if title_node
        else _title_from_html(html) or _fallback_slug(url)
    )
    article_soup = BeautifulSoup("<article></article>", "html.parser")
    article = article_soup.article
    if article is None:
        return title, str(body)
    heading = article_soup.new_tag("h1")
    heading.string = title
    article.append(heading)
    article.append(body)
    return title, str(article)


def _image_extension(image_url: str) -> str:
    suffix = Path(urlparse(image_url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}:
        return suffix
    return ".jpg"


def _path_from_file_url(file_url: str) -> Path:
    parsed = urlparse(file_url)
    return Path(url2pathname(parsed.path))
