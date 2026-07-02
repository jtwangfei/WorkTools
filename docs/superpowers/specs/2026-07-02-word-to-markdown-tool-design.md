# Word to Markdown Tool Design

## Goal

Build a Python command-line tool that converts a Word `.docx` file into a Markdown `.md` file while preserving common document structure and writing Word formulas as LaTeX math in Markdown.

The first version should focus on reliable conversion through Pandoc instead of custom Word parsing. It should handle headings, paragraphs, bold and italic text, lists, tables, images, and equations as well as Pandoc supports them.

## User Workflow

Convert one document with default output paths:

```powershell
python -m worktools.word_to_markdown_cli D:\Docs\report.docx
```

Default output:

```text
exports/markdown/
  report/
    report.md
    media/
      image1.png
```

Convert to an explicit Markdown path:

```powershell
python -m worktools.word_to_markdown_cli D:\Docs\report.docx -o D:\Notes\report.md
```

Replace an existing output:

```powershell
python -m worktools.word_to_markdown_cli D:\Docs\report.docx -o D:\Notes\report.md --overwrite
```

## Recommended Approach

Use Pandoc as the conversion engine and keep the project code as a thin, tested wrapper.

The core module should call Pandoc with:

```text
pandoc input.docx --from docx --to gfm+tex_math_dollars --extract-media <output-dir> -o output.md
```

This keeps the implementation small and avoids reimplementing `.docx` structure, table conversion, image extraction, and OMML math conversion in Python.

## Alternatives Considered

### Pure Python Parsing

Use `python-docx` to read paragraphs, headings, runs, tables, and images, then write Markdown manually.

This is not recommended because formulas and complex Word structures are difficult to preserve correctly. It would add more code and more edge cases than the current requirement needs.

### Hybrid Parser

Use Python for document structure and parse Word OMML XML separately for formulas.

This is also not recommended for the first version. It is more controllable than plain `python-docx`, but still too complex for a practical utility whose core behavior Pandoc already provides.

## Architecture

Add:

```text
src/worktools/word_to_markdown.py      # Core conversion logic and path validation
src/worktools/word_to_markdown_cli.py  # Thin argparse wrapper
tests/test_word_to_markdown.py         # Unit tests for core behavior and CLI parsing
```

The CLI module should only parse arguments, build options, call the core function, and print success or error messages.

The core module should own:

- Input validation.
- Output path selection.
- Existing output protection.
- Pandoc command construction.
- Subprocess execution.
- Clear errors for missing Pandoc or failed conversion.

## Data Flow

1. CLI receives a `.docx` path.
2. CLI builds `WordToMarkdownOptions`.
3. Core validates the input file exists and has the `.docx` suffix.
4. Core resolves the output Markdown path.
5. Core rejects an existing output unless `overwrite=True`.
6. Core creates the output directory.
7. Core runs Pandoc with GitHub-Flavored Markdown plus dollar-delimited TeX math.
8. Core returns a result containing the Markdown path and media directory.

## Output Rules

If `-o/--output` is provided:

- It must be the final `.md` file path.
- The media directory is `<output parent>/media`.

If no output is provided:

- Use `exports/markdown/<input-stem>/<input-stem>.md`.
- Use `exports/markdown/<input-stem>/media`.

If the output Markdown file exists and `--overwrite` is not set, fail before running Pandoc.

## Error Handling

Raise project-specific errors for:

- Input file does not exist.
- Input is not a `.docx` file.
- Output file already exists without `--overwrite`.
- Pandoc is not installed or not on `PATH`.
- Pandoc exits with a non-zero status.

The CLI should catch these errors, print `Error: ...` to stderr, and return exit code `1`.

## Testing

Use TDD.

Core tests should avoid requiring a real Pandoc binary by injecting a command runner. Tests should verify:

- Default output paths are derived from the input filename.
- Explicit output paths are respected.
- Non-`.docx` inputs are rejected.
- Existing output is rejected unless overwrite is enabled.
- The Pandoc command includes `--from docx`, `--to gfm+tex_math_dollars`, `--extract-media`, and `-o`.
- Missing Pandoc is converted into a clear project error.
- Pandoc failure is converted into a clear project error.

CLI tests should verify:

- Arguments are converted into expected options.
- Successful conversion prints the saved Markdown and media paths.
- Conversion errors return non-zero and print to stderr.

## Success Criteria

- A user can run a command to convert a `.docx` file into Markdown.
- Common Word structure is delegated to Pandoc and preserved as Markdown where supported.
- Word equations are emitted as LaTeX math in Markdown through Pandoc's Markdown writer.
- Images are extracted into a local `media/` directory.
- The implementation stays small and matches the existing Python CLI style.
- Tests cover validation, path behavior, Pandoc command construction, and CLI error handling.
