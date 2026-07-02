# Word Merge Tool Design

## Purpose

Build a Python command-line tool that merges multiple Word `.docx` files into a selected Word template. The first version focuses on deterministic template-based merging. It reserves a command option for future content summarization, but does not implement AI or semantic summarization yet.

The tool is intended for daily document assembly tasks where the final document must follow a strict template format.

## Command

Merge documents by template name:

```powershell
python -m worktools.word_merge_cli --template report input1.docx input2.docx -o merged.docx
```

Merge documents by template path:

```powershell
python -m worktools.word_merge_cli --template D:\templates\report.docx input1.docx -o merged.docx
```

`--mode direct` is the default behavior:

```powershell
python -m worktools.word_merge_cli --template report input1.docx -o merged.docx --mode direct
```

`--mode summarize` is reserved for a later version. In the first version, using it fails with a clear "not implemented" error.

## Template Resolution

The `--template` value supports both paths and template names.

If the value points to an existing file, the tool uses it directly. Otherwise, the tool treats the value as a template name and looks under the default `templates/` directory:

```text
templates/report.docx
templates/report.dotx
```

The first version uses the current working directory as the base for the default `templates/` directory.

## Template Contract

The template must contain one `{{content}}` placeholder. The placeholder marks where merged source content should be inserted.

The placeholder must be the only text in its paragraph. The inserted content uses the style from that placeholder paragraph so the output follows the template format strictly.

If the placeholder appears multiple times, the command fails instead of guessing which location to use.

## Merge Behavior

The tool reads each input `.docx` in the order provided on the command line. It inserts their content at the `{{content}}` placeholder position.

The first version supports:

- Paragraph text.
- Heading paragraphs as ordinary inserted paragraphs using the template placeholder style.
- Basic list paragraphs as ordinary inserted paragraphs using the template placeholder style.

The first version does not promise full fidelity for complex Word features, including:

- Comments.
- Track changes.
- Footnotes or endnotes.
- Table of contents fields.
- Tables.
- Embedded objects.
- Complete image relationship migration.

This keeps the first version reliable and avoids claiming support for Word features that require lower-level package relationship handling.

## Output Handling

The output path is required through `-o` or `--output`.

If the output file already exists, the command fails unless `--overwrite` is provided.

The command creates the output parent directory if needed.

## CLI Options

Initial options:

- `--template`: required template name or `.docx` / `.dotx` template path.
- `inputs`: one or more source `.docx` files.
- `-o, --output`: required output `.docx` file path.
- `--mode`: merge mode, either `direct` or `summarize`; default `direct`.
- `--overwrite`: replace an existing output file.

## Code Structure

```text
src/worktools/word_merge.py       # Core logic for template resolution, validation, and merging
src/worktools/word_merge_cli.py   # Thin CLI wrapper around the core module
tests/test_word_merge.py          # Unit tests for resolution, validation, and merge behavior
```

The CLI module should stay thin. The merge module should expose testable functions so tests can generate temporary Word files without invoking subprocesses.

## Error Handling

The command should fail clearly when:

- The template cannot be found.
- The template has no `{{content}}` placeholder.
- The template has more than one `{{content}}` placeholder.
- The `{{content}}` placeholder is not the only text in its paragraph.
- An input file does not exist.
- An input file is not a `.docx` file.
- The output file exists and `--overwrite` is not provided.
- `--mode summarize` is requested.
- A document cannot be read or written by `python-docx`.

## Dependencies

Use `python-docx` for reading and writing Word documents.

Do not add an AI dependency in the first version. Summarization remains a reserved mode only.

## Tests

Tests should generate temporary `.docx` files with `python-docx` and should not depend on Microsoft Office.

Tests should cover:

- Template name resolution to `templates/report.docx`.
- Template path resolution.
- Missing placeholder error.
- Duplicate placeholder error.
- Missing input file error.
- Non-`.docx` input rejection.
- Existing output rejection without `--overwrite`.
- Multiple input documents inserted in command-line order.
- Inserted paragraphs using the placeholder paragraph style.
- `--mode summarize` returning a not implemented error.

## Success Criteria

The first version is complete when:

- A user can merge one or more `.docx` files into a template containing `{{content}}`.
- Template names and template paths both work.
- Direct merge output follows the placeholder paragraph style from the template.
- Reserved summarize mode fails explicitly instead of silently doing the wrong thing.
- Unit tests cover the main merge path and expected failure modes.
