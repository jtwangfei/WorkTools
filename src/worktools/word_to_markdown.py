from __future__ import annotations

import re
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from subprocess import CalledProcessError


class WordToMarkdownError(RuntimeError):
    """Base error for Word to Markdown conversion failures."""


class InputDocumentError(WordToMarkdownError):
    """Raised when the input document is invalid."""


class OutputExistsError(WordToMarkdownError):
    """Raised when the output already exists and overwrite is disabled."""


class PandocNotFoundError(WordToMarkdownError):
    """Raised when the pandoc executable cannot be found."""


class PandocConversionError(WordToMarkdownError):
    """Raised when pandoc fails to convert the document."""


class FormulaImageOcrError(WordToMarkdownError):
    """Raised when formula image OCR cannot run."""


@dataclass(frozen=True)
class WordToMarkdownOptions:
    input_path: Path
    output: Path | None = None
    overwrite: bool = False
    output_dir: Path = Path("exports/markdown")
    formula_ocr_python: Path | None = None
    formula_ocr_device: str = "cpu"


@dataclass(frozen=True)
class WordToMarkdownResult:
    markdown_path: Path
    media_dir: Path
    warnings: tuple[str, ...] = ()


Runner = Callable[[list[str]], None]
FormulaImageOcr = Callable[[list[Path]], dict[Path, str]]


def convert_word_to_markdown(
    options: WordToMarkdownOptions,
    *,
    runner: Runner | None = None,
    formula_image_ocr: FormulaImageOcr | None = None,
) -> WordToMarkdownResult:
    input_path = options.input_path
    _validate_input(input_path)

    markdown_path, media_dir, extract_dir = _resolve_paths(options)
    if markdown_path.exists() and not options.overwrite:
        raise OutputExistsError(f"Output already exists: {markdown_path}")

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "pandoc",
        str(input_path),
        "--from",
        "docx",
        "--to",
        "markdown+tex_math_dollars",
        "--extract-media",
        str(extract_dir),
        "-o",
        str(markdown_path),
    ]

    try:
        (runner or _run_pandoc)(command)
    except FileNotFoundError as exc:
        raise PandocNotFoundError("Pandoc executable not found on PATH.") from exc
    except CalledProcessError as exc:
        message = exc.stderr or str(exc)
        raise PandocConversionError(f"Pandoc conversion failed: {message}") from exc

    _normalize_media_links(markdown_path, extract_dir)
    ocr_warnings: tuple[str, ...] = ()
    remaining_media_count: int | None = None
    formula_ocr = formula_image_ocr
    if formula_ocr is None and options.formula_ocr_python is not None:
        formula_ocr = lambda image_paths: _recognize_formula_images(
            image_paths,
            options.formula_ocr_python,
            options.formula_ocr_device,
        )
    if formula_ocr is not None:
        remaining_media_count, ocr_warnings = _replace_formula_images_with_latex(
            markdown_path,
            media_dir,
            formula_ocr,
        )

    return WordToMarkdownResult(
        markdown_path=markdown_path,
        media_dir=media_dir,
        warnings=ocr_warnings + _build_warnings(media_dir, remaining_media_count),
    )


def _run_pandoc(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True, text=True)


def _validate_input(input_path: Path) -> None:
    if not input_path.is_file():
        raise InputDocumentError(f"Input document not found: {input_path}")
    if input_path.suffix.lower() != ".docx":
        raise InputDocumentError(f"Input document must be a .docx file: {input_path}")


def _resolve_paths(options: WordToMarkdownOptions) -> tuple[Path, Path, Path]:
    if options.output is not None:
        markdown_path = options.output
        media_dir = markdown_path.parent / "media"
        return markdown_path, media_dir, markdown_path.parent

    article_dir = options.output_dir / options.input_path.stem
    markdown_path = article_dir / f"{options.input_path.stem}.md"
    media_dir = article_dir / "media"
    return markdown_path, media_dir, article_dir


def _normalize_media_links(markdown_path: Path, extract_dir: Path) -> None:
    if not markdown_path.is_file():
        return

    content = markdown_path.read_text(encoding="utf-8")
    pattern = re.compile(_path_regex(extract_dir) + r"[\\/]media[\\/]")
    normalized = pattern.sub("./media/", content)
    normalized = re.sub(
        r"(?m)^\$\$(?=!\[[^\]]*\]\(\./media/|<img\s+src=[\"']\./media/)",
        "",
        normalized,
    )
    if normalized != content:
        markdown_path.write_text(normalized, encoding="utf-8")


def _path_regex(path: Path) -> str:
    parts = [part for part in re.split(r"[\\/]+", str(path)) if part]
    return r"[\\/]".join(re.escape(part) for part in parts)


_MEDIA_IMAGE_PATTERN = re.compile(
    r"!\[[^\]]*\]\(\./media/([^)]+)\)(?:\{[^}]*\})?"
    r"|<img\s+src=[\"']\./media/([^\"']+)[\"'][^>]*>",
    re.IGNORECASE,
)


def _replace_formula_images_with_latex(
    markdown_path: Path,
    media_dir: Path,
    formula_image_ocr: FormulaImageOcr,
) -> tuple[int, tuple[str, ...]]:
    if not markdown_path.is_file():
        return 0, ()

    content = markdown_path.read_text(encoding="utf-8")
    image_paths = _find_referenced_media_images(content, media_dir)
    if not image_paths:
        return 0, ()

    warnings: tuple[str, ...] = ()
    try:
        formulas = formula_image_ocr(image_paths)
    except FormulaImageOcrError as exc:
        formulas = {}
        warnings = (f"Formula image OCR failed: {exc}",)

    def replace_match(match: re.Match[str]) -> str:
        image_path = _media_path_from_match(match, media_dir)
        formula = _normalize_recognized_latex(formulas.get(image_path, ""))
        if not formula:
            return match.group(0)
        if _is_standalone_match(content, match):
            return f"$${formula}$$"
        return f"${formula}$"

    updated = _MEDIA_IMAGE_PATTERN.sub(replace_match, content)
    if updated != content:
        markdown_path.write_text(updated, encoding="utf-8")

    return len(_find_referenced_media_images(updated, media_dir)), warnings


def _find_referenced_media_images(content: str, media_dir: Path) -> list[Path]:
    image_paths: list[Path] = []
    seen: set[Path] = set()
    for match in _MEDIA_IMAGE_PATTERN.finditer(content):
        image_path = _media_path_from_match(match, media_dir)
        if image_path not in seen:
            image_paths.append(image_path)
            seen.add(image_path)
    return image_paths


def _media_path_from_match(match: re.Match[str], media_dir: Path) -> Path:
    media_name = match.group(1) or match.group(2)
    return media_dir / media_name.replace("/", "\\")


def _is_standalone_match(content: str, match: re.Match[str]) -> bool:
    line_start = content.rfind("\n", 0, match.start()) + 1
    line_end = content.find("\n", match.end())
    if line_end == -1:
        line_end = len(content)
    return (
        content[line_start : match.start()].strip() == ""
        and content[match.end() : line_end].strip() == ""
    )


def _recognize_formula_images(
    image_paths: list[Path],
    formula_ocr_python: Path,
    formula_ocr_device: str,
) -> dict[Path, str]:
    if not formula_ocr_python.is_file():
        raise FormulaImageOcrError(f"Python executable not found: {formula_ocr_python}")

    with tempfile.TemporaryDirectory() as temp_dir:
        prepared_images = _prepare_formula_ocr_images(image_paths, Path(temp_dir))
        command = [
            str(formula_ocr_python),
            "-c",
            _FORMULA_OCR_SCRIPT,
            formula_ocr_device,
            *[str(prepared) for _, prepared in prepared_images],
        ]
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except CalledProcessError as exc:
            message = exc.stderr or exc.stdout or str(exc)
            raise FormulaImageOcrError(message) from exc

        recognized_by_prepared_path = _parse_formula_ocr_output(completed.stdout)
        return {
            original: _normalize_recognized_latex(formula)
            for original, prepared in prepared_images
            if (formula := recognized_by_prepared_path.get(str(prepared)))
        }


def _prepare_formula_ocr_images(image_paths: list[Path], temp_dir: Path) -> list[tuple[Path, Path]]:
    prepared_images: list[tuple[Path, Path]] = []
    for index, image_path in enumerate(image_paths, start=1):
        if image_path.suffix.lower() == ".emf":
            prepared_path = temp_dir / f"formula-{index}.png"
            _convert_emf_to_png(image_path, prepared_path)
        else:
            prepared_path = image_path
        prepared_images.append((image_path, prepared_path))
    return prepared_images


def _convert_emf_to_png(input_path: Path, output_path: Path) -> None:
    script_path = output_path.with_suffix(".ps1")
    script = r"""
param($InputPath, $OutputPath)
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile($InputPath)
try {
    $bmp = New-Object System.Drawing.Bitmap $img.Width, $img.Height
    $graphics = [System.Drawing.Graphics]::FromImage($bmp)
    try {
        $graphics.Clear([System.Drawing.Color]::White)
        $graphics.DrawImage($img, 0, 0, $img.Width, $img.Height)
        $bmp.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $graphics.Dispose()
        $bmp.Dispose()
    }
} finally {
    $img.Dispose()
}
"""
    script_path.write_text(script, encoding="utf-8")
    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                str(input_path),
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except CalledProcessError as exc:
        message = exc.stderr or exc.stdout or str(exc)
        raise FormulaImageOcrError(f"Could not convert EMF to PNG: {message}") from exc
    finally:
        script_path.unlink(missing_ok=True)

    if not output_path.is_file():
        raise FormulaImageOcrError(f"Could not convert EMF to PNG: {input_path}")


def _parse_formula_ocr_output(output: str) -> dict[str, str]:
    marker = "WORKTOOLS_FORMULA_OCR_JSON="
    for line in reversed(output.splitlines()):
        if line.startswith(marker):
            import json

            parsed = json.loads(line[len(marker) :])
            return {str(path): str(formula) for path, formula in parsed.items()}
    raise FormulaImageOcrError("Formula OCR did not return parseable JSON output.")


def _normalize_recognized_latex(formula: str) -> str:
    normalized = formula.strip()
    normalized = re.sub(r"\be\s*x\s*p\b", r"\\exp", normalized)
    normalized = re.sub(r"\bl\s*n\b", r"\\ln", normalized)
    normalized = re.sub(r"\\+(?=(?:exp|ln)\b)", r"\\", normalized)

    def compact_simple_subscript(match: re.Match[str]) -> str:
        value = match.group(1)
        if re.fullmatch(r"[A-Za-z0-9 ]+", value):
            return "_{" + value.replace(" ", "") + "}"
        return match.group(0)

    return re.sub(r"_\{([^{}]+)\}", compact_simple_subscript, normalized)


_FORMULA_OCR_SCRIPT = r"""
import json
import sys

from paddleocr import FormulaRecognition

device = sys.argv[1]
image_paths = sys.argv[2:]
recognizer = FormulaRecognition(device=device)
recognized = {}
for image_path in image_paths:
    result = recognizer.predict(image_path)
    formula = ""
    if result:
        formula = str(result[0].get("rec_formula", "")).strip()
    if formula:
        recognized[image_path] = formula
print("WORKTOOLS_FORMULA_OCR_JSON=" + json.dumps(recognized, ensure_ascii=False))
"""


def _build_warnings(media_dir: Path, media_count: int | None = None) -> tuple[str, ...]:
    if not media_dir.is_dir():
        return ()

    if media_count is None:
        media_count = sum(1 for path in media_dir.iterdir() if path.is_file())
    if media_count == 0:
        return ()

    return (
        f"{media_count} media file(s) were extracted and kept as images; "
        "image-based formulas are not converted to LaTeX.",
    )
