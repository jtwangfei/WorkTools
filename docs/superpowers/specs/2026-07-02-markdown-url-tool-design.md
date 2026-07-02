# Markdown URL Tool Design

## Purpose

Build a Python command-line tool that converts a general web article URL into a local Markdown archive. The tool is for collecting useful work-related articles, documents, and notes in a clean offline format.

## Command

```powershell
python -m worktools.markdown_url "https://example.com/article"
```

Optional output directory:

```powershell
python -m worktools.markdown_url "https://example.com/article" -o D:\Articles
```

If `-o` is not provided, the tool writes to `exports/markdown/`.

## Output Layout

Each article gets its own folder under the output root:

```text
exports/markdown/
  article-title/
    article-title.md
    images/
      image-001.jpg
      image-002.png
```

The article folder name and Markdown filename are generated from the page title. If the title is missing, the tool uses the URL host plus a timestamp. Filenames are sanitized for Windows and common filesystem compatibility.

Markdown image references use relative paths:

```markdown
![image](images/image-001.jpg)
```

## Content Extraction

The tool targets general article pages such as blogs, documentation pages, and news articles. It should extract the main article body and avoid navigation, sidebars, footers, ads, recommendations, and unrelated links.

Implementation will use:

- `requests` for downloading pages and images.
- `trafilatura` for main-content extraction.
- `beautifulsoup4` for inspecting and rewriting image elements.
- `markdownify` for converting cleaned HTML to Markdown.

Normal hyperlinks are removed by default while preserving their visible text. Image links are kept only when they belong to the extracted article body.

## Image Handling

The tool downloads images found in the extracted article body into the article's `images/` directory. It resolves relative image URLs against the source page URL.

Image filenames are assigned in article order:

```text
image-001.jpg
image-002.png
```

The extension is inferred from the response content type or URL path. If an image cannot be downloaded, the tool skips that image and continues processing the article. A concise warning is printed so the user knows the archive may be incomplete.

## Error Handling

The command should fail clearly when:

- The URL cannot be fetched.
- Main content cannot be extracted.
- The output article folder already exists and `--overwrite` is not provided.
- The Markdown file cannot be written.

The command should continue with warnings when:

- One or more images cannot be downloaded.
- An image URL is malformed.
- An image has an unknown extension.

## CLI Options

Initial options:

- `url`: required article URL.
- `-o, --output-dir`: output root directory, default `exports/markdown/`.
- `--overwrite`: replace an existing article folder.
- `--timeout`: request timeout in seconds, default `20`.
- `--keep-links`: keep normal hyperlinks in Markdown. By default links are converted to plain text.

## Code Structure

```text
src/worktools/markdown_url.py      # CLI entry point
src/worktools/web_to_markdown.py   # Fetching, extraction, conversion, image archiving
tests/test_web_to_markdown.py      # Unit tests for naming, rewriting, and conversion behavior
```

The CLI module should stay thin. Most behavior belongs in `web_to_markdown.py` so it can be tested without invoking subprocesses.

## Tests

Tests should cover:

- Safe filename generation.
- Output folder path generation.
- Relative image URL resolution.
- Markdown image path rewriting.
- Link removal while preserving visible text.
- Existing output folder behavior with and without overwrite.

Network calls should be isolated behind functions that can be mocked. Unit tests should not depend on live websites.
