# Markdown URL Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that archives a general article URL as Markdown plus local body images.

**Architecture:** Keep the CLI thin in `src/worktools/markdown_url.py`. Put URL fetching, content extraction, Markdown conversion, image downloading, output folder creation, and filename helpers in `src/worktools/web_to_markdown.py` so unit tests can call behavior directly without live websites.

**Tech Stack:** Python 3.10+, `requests`, `trafilatura`, `beautifulsoup4`, `markdownify`, `pytest`, `ruff`.

---

### Task 1: Core Helpers

**Files:**
- Create: `tests/test_web_to_markdown.py`
- Create: `src/worktools/web_to_markdown.py`

- [ ] **Step 1: Write failing tests**

Add tests for filename sanitizing, article directory selection, link stripping, and image URL rewriting.

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_web_to_markdown.py -v`

Expected: FAIL because `worktools.web_to_markdown` does not exist.

- [ ] **Step 3: Implement helper functions**

Implement `sanitize_filename`, `build_archive_paths`, `rewrite_html_for_markdown`, and supporting data structures.

- [ ] **Step 4: Verify green**

Run: `python -m pytest tests/test_web_to_markdown.py -v`

Expected: PASS.

### Task 2: Article Archiving Flow

**Files:**
- Modify: `tests/test_web_to_markdown.py`
- Modify: `src/worktools/web_to_markdown.py`

- [ ] **Step 1: Write failing tests**

Add tests for successful archive creation using injected fetch, extract, and image download functions, plus existing folder behavior with and without overwrite.

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_web_to_markdown.py -v`

Expected: FAIL because `archive_url` is missing or incomplete.

- [ ] **Step 3: Implement archive flow**

Implement `archive_url`, default fetchers, image download behavior, extension inference, warnings, and clear custom errors.

- [ ] **Step 4: Verify green**

Run: `python -m pytest tests/test_web_to_markdown.py -v`

Expected: PASS.

### Task 3: CLI

**Files:**
- Create: `tests/test_markdown_url_cli.py`
- Create: `src/worktools/markdown_url.py`

- [ ] **Step 1: Write failing CLI tests**

Add tests for argument parsing success and non-zero error output.

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_markdown_url_cli.py -v`

Expected: FAIL because `worktools.markdown_url` does not exist.

- [ ] **Step 3: Implement CLI**

Implement `main(argv=None)` with `argparse`, `--output-dir`, `--overwrite`, `--timeout`, and `--keep-links`.

- [ ] **Step 4: Verify green**

Run: `python -m pytest tests/test_markdown_url_cli.py -v`

Expected: PASS.

### Task 4: Dependencies and Documentation

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`

- [ ] **Step 1: Update dependencies**

Add runtime dependencies: `beautifulsoup4`, `markdownify`, `requests`, and `trafilatura`.

- [ ] **Step 2: Update README**

Document the Markdown URL tool command, output layout, and image behavior.

- [ ] **Step 3: Install and verify**

Run:

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

Expected: all commands exit 0.

### Task 5: Final Verification

**Files:**
- All changed files

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest`

Expected: all tests pass.

- [ ] **Step 2: Run lint**

Run: `python -m ruff check .`

Expected: all checks pass.

- [ ] **Step 3: Review git status**

Run: `git status --short --branch`

Expected: only intended repository files are changed or untracked.
