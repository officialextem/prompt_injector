import pytest

from prompt_injector.app import parser
from prompt_injector.app.parser import ParserError, estimate_tokens, load_prompt_blocks, parse_prompt_blocks


def test_parse_numbered_prompt_headings() -> None:
    prompts = parse_prompt_blocks(
        """
PROMPT 0
Erster Auftrag

PROMPT 1
Zweiter Auftrag
"""
    )

    assert [prompt.title for prompt in prompts] == ["PROMPT 0", "PROMPT 1"]
    assert prompts[0].content == "Erster Auftrag"
    assert prompts[1].content == "Zweiter Auftrag"


def test_parse_markdown_and_emoji_prompt_headings() -> None:
    prompts = parse_prompt_blocks(
        """
## PROMPT 2
Markdown Inhalt

### 📦 PROMPT 3: Basis-Architektur
Architektur Inhalt

🔍 PROMPT 4: Fenster-Erkennung
Fenster Inhalt
"""
    )

    assert len(prompts) == 3
    assert prompts[0].content == "Markdown Inhalt"
    assert prompts[1].label == "PROMPT 3"
    assert prompts[1].title == "Basis-Architektur"
    assert prompts[2].label == "PROMPT 4"
    assert prompts[2].title == "Fenster-Erkennung"


def test_parse_is_case_insensitive() -> None:
    prompts = parse_prompt_blocks(
        """
Prompt 1
Kleinschreibung
"""
    )

    assert len(prompts) == 1
    assert prompts[0].label == "PROMPT 1"
    assert prompts[0].title == "PROMPT 1"
    assert prompts[0].content == "Kleinschreibung"


def test_single_document_without_markers_becomes_prompt_zero() -> None:
    prompts = parse_prompt_blocks("Ein einzelner langer Prompt")

    assert len(prompts) == 1
    assert prompts[0].label == "PROMPT 0"
    assert prompts[0].content == "Ein einzelner langer Prompt"


def test_empty_text_returns_empty_list() -> None:
    assert parse_prompt_blocks("") == []
    assert parse_prompt_blocks("   \n\t") == []


def test_empty_prompt_blocks_are_ignored() -> None:
    prompts = parse_prompt_blocks(
        """
PROMPT 0

PROMPT 1
Inhalt
"""
    )

    assert len(prompts) == 1
    assert prompts[0].label == "PROMPT 1"
    assert prompts[0].index == 0


def test_estimate_tokens_is_rough_character_based_estimate() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcdefgh") == 2


class FakePage:
    def __init__(self, text: str) -> None:
        self.text = text

    def get_text(self, mode: str) -> str:
        assert mode == "text"
        return self.text


class FakeDocument:
    def __init__(self, pages: list[FakePage]) -> None:
        self.pages = pages
        self.closed = False

    def __iter__(self):
        return iter(self.pages)

    def close(self) -> None:
        self.closed = True


class FakeFitz:
    def __init__(self, document: FakeDocument) -> None:
        self.document = document

    def open(self, _path):
        return self.document


def test_load_pdf_uses_extracted_text_and_existing_parser(monkeypatch, tmp_path) -> None:
    pdf_path = tmp_path / "prompts.pdf"
    pdf_path.write_bytes(b"%PDF-test")
    document = FakeDocument(
        [
            FakePage("PROMPT 0\nAus PDF Seite 1"),
            FakePage("PROMPT 1: PDF Titel\nAus PDF Seite 2"),
        ]
    )
    monkeypatch.setattr(parser, "fitz", FakeFitz(document))

    prompts = load_prompt_blocks(pdf_path)

    assert document.closed is True
    assert len(prompts) == 2
    assert prompts[0].content == "Aus PDF Seite 1"
    assert prompts[1].title == "PDF Titel"
    assert prompts[1].content == "Aus PDF Seite 2"


def test_pdf_without_extractable_text_raises_clear_error(monkeypatch, tmp_path) -> None:
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-test")
    monkeypatch.setattr(parser, "fitz", FakeFitz(FakeDocument([FakePage("   ")])))

    with pytest.raises(ParserError, match="keinen extrahierbaren Text"):
        load_prompt_blocks(pdf_path)


def test_pdf_import_without_pymupdf_raises_clear_error(monkeypatch, tmp_path) -> None:
    pdf_path = tmp_path / "prompts.pdf"
    pdf_path.write_bytes(b"%PDF-test")
    monkeypatch.setattr(parser, "fitz", None)

    with pytest.raises(ParserError, match="PyMuPDF fehlt"):
        load_prompt_blocks(pdf_path)
