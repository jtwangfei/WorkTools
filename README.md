# WorkTools

WorkTools is a Python repository for small utilities that improve daily work efficiency and solve practical workflow problems.

## Project Goals

- Collect reusable scripts and command-line tools.
- Keep shared logic in importable Python modules.
- Make tools easy to run, test, and maintain.
- Document each tool well enough for future reuse.

## Repository Structure

```text
.
├── .github/              # GitHub templates and CI workflows
├── docs/                 # Documentation and usage notes
├── scripts/              # Directly runnable utility scripts
├── src/worktools/        # Reusable Python package code
├── tests/                # Automated tests
├── pyproject.toml        # Python project metadata and tool config
├── requirements.txt      # Runtime dependencies
└── README.md             # Project overview
```

## Getting Started

Create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project in editable mode:

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

Run tests:

```powershell
python -m pytest
```

## Markdown URL Tool

Archive a general web article as a local Markdown file with downloaded body images:

```powershell
python -m worktools.markdown_url "https://example.com/article"
```

By default, output is written under `exports/markdown/`:

```text
exports/markdown/
  article-title/
    article-title.md
    images/
      image-001.jpg
      image-002.png
```

Use a custom output root:

```powershell
python -m worktools.markdown_url "https://example.com/article" -o D:\Articles
```

If a site blocks automated fetching, save the article page from a logged-in browser as a
complete webpage, then convert that HTML file:

```powershell
python -m worktools.markdown_url --html-file D:\Downloads\article.html
```

Use `--source-url "https://example.com/article"` only when the saved HTML still points to
remote relative assets instead of local files.

Useful options:

- `--overwrite`: replace an existing article folder.
- `--timeout 30`: set request timeout in seconds.
- `--keep-links`: keep normal hyperlinks. By default, links are converted to plain text while images are saved locally.

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

## Adding a New Tool

1. Put quick standalone scripts in `scripts/`.
2. Put reusable logic in `src/worktools/`.
3. Add tests under `tests/`.
4. Add usage notes in `docs/` or this README when the tool becomes useful to others.

## License

This project is licensed under the MIT License. See `LICENSE` for details.
