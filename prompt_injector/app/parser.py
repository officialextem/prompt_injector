from __future__ import annotations

import re
from pathlib import Path

from prompt_injector.app.models import PromptBlock

try:
    import fitz
except ImportError:  # pragma: no cover - wird ueber Tests per Monkeypatch abgedeckt.
    fitz = None

SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md"}
SUPPORTED_EXTENSIONS = SUPPORTED_TEXT_EXTENSIONS | {".pdf"}
PROMPT_HEADER_PATTERN = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]*)?(?:[^\w\r\n]*[ \t]*)?"
    r"(?P<label>prompt[ \t]+(?P<number>\d+))"
    r"(?:[ \t]*:[ \t]*(?P<title>.+?))?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)


class ParserError(ValueError):
    """Fehler beim Lesen oder Erkennen von Prompt-Dateien."""


def load_text_file(path: Path) -> str:
    if path.suffix.lower() not in SUPPORTED_TEXT_EXTENSIONS:
        raise ParserError(f"Dateityp wird noch nicht unterstuetzt: {path.suffix or 'ohne Endung'}")
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ParserError(f"Datei konnte nicht gelesen werden: {path}") from exc


def extract_pdf_text(path: Path) -> str:
    if fitz is None:
        raise ParserError("PyMuPDF fehlt. Bitte Abhaengigkeiten mit `pip install -r requirements.txt` installieren.")

    try:
        document = fitz.open(path)
    except Exception as exc:
        raise ParserError(f"PDF konnte nicht geoeffnet werden: {path}") from exc

    try:
        page_texts: list[str] = []
        for page in document:
            page_texts.append(page.get_text("text"))
    except Exception as exc:
        raise ParserError(f"PDF-Text konnte nicht extrahiert werden: {path}") from exc
    finally:
        document.close()

    text = "\n\n".join(page_text.strip() for page_text in page_texts if page_text.strip()).strip()
    if not text:
        raise ParserError("Diese PDF enthaelt keinen extrahierbaren Text. OCR ist in v0.1 noch nicht enthalten.")
    return text


def load_prompt_source(path: Path) -> str:
    extension = path.suffix.lower()
    if extension in SUPPORTED_TEXT_EXTENSIONS:
        return load_text_file(path)
    if extension == ".pdf":
        return extract_pdf_text(path)
    raise ParserError(f"Dateityp wird noch nicht unterstuetzt: {extension or 'ohne Endung'}")


def estimate_tokens(text: str) -> int:
    clean_text = text.strip()
    if not clean_text:
        return 0
    return max(1, len(clean_text) // 4)


def parse_prompt_blocks(text: str) -> list[PromptBlock]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    matches = list(PROMPT_HEADER_PATTERN.finditer(normalized))
    if not matches:
        return [
            PromptBlock(
                index=0,
                label="PROMPT 0",
                title="PROMPT 0",
                content=normalized,
            )
        ]

    blocks: list[PromptBlock] = []
    for match_index, match in enumerate(matches):
        content_start = match.end()
        content_end = matches[match_index + 1].start() if match_index + 1 < len(matches) else len(normalized)
        content = normalized[content_start:content_end].strip()
        if not content:
            continue

        number = match.group("number")
        label = f"PROMPT {number}"
        raw_title = match.group("title")
        title = raw_title.strip() if raw_title and raw_title.strip() else label
        blocks.append(
            PromptBlock(
                index=len(blocks),
                label=label,
                title=title,
                content=content,
            )
        )

    return blocks


def load_prompt_blocks(path: Path) -> list[PromptBlock]:
    return parse_prompt_blocks(load_prompt_source(path))
