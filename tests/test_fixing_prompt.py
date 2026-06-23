from prompt_injector.app.fixing_prompt import FIXING_PROMPT


def test_fixing_prompt_contains_required_prompt_header_format() -> None:
    assert "# PROMPT 0: Kurzer Titel" in FIXING_PROMPT
    assert "Gib nur die neu formatierte Prompt-Kette aus." in FIXING_PROMPT
    assert "Hier ist die unsaubere Prompt-Kette:" in FIXING_PROMPT
