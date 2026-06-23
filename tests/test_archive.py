import json

import pytest

from prompt_injector.app.archive import ArchiveError, save_manual_response
from prompt_injector.app.models import PromptBlock, PromptSession


def test_save_manual_response_writes_prompt_response_and_summary(tmp_path) -> None:
    session = PromptSession.empty()
    session.source_file = "C:/Prompts/source.md"
    prompt = PromptBlock(index=2, label="PROMPT 2", title="Titel", content="Prompt Inhalt", status="done")
    session.prompts.extend(
        [
            PromptBlock(index=0, label="PROMPT 0", title="Start", content="A"),
            prompt,
        ]
    )
    session_file = tmp_path / "session_2026-01-01_10-00-00.json"

    result = save_manual_response(session, prompt, "Antwort Inhalt", session_file, runs_dir=tmp_path)

    assert result.run_dir == tmp_path / "session_2026-01-01_10-00-00"
    assert result.prompt_file.name == "prompt_02.md"
    assert result.response_file.name == "response_02.md"
    assert "Prompt Inhalt" in result.prompt_file.read_text(encoding="utf-8")
    assert result.response_file.read_text(encoding="utf-8") == "Antwort Inhalt\n"

    summary = json.loads(result.summary_file.read_text(encoding="utf-8"))
    assert summary["session_file"] == str(session_file)
    assert summary["source_file"] == "C:/Prompts/source.md"
    assert summary["prompt_count"] == 2
    assert summary["response_files"] == ["response_02.md"]
    assert summary["prompt_status"][1]["status"] == "done"


def test_save_manual_response_rejects_empty_response(tmp_path) -> None:
    session = PromptSession.empty()
    prompt = PromptBlock(index=0, label="PROMPT 0", title="Start", content="Prompt")

    with pytest.raises(ArchiveError, match="Leere Antworten"):
        save_manual_response(session, prompt, "   ", None, runs_dir=tmp_path)
