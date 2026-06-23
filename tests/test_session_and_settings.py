import pytest

from prompt_injector.app.models import InjectorSettings, PromptBlock, PromptSession
from prompt_injector.app.session_manager import (
    SESSION_FILENAME_PREFIX,
    SessionError,
    load_session,
    save_session,
    save_session_as_timestamped_file,
)
from prompt_injector.app.settings import SettingsError, load_settings, save_settings


def test_session_save_and_load_roundtrip(tmp_path) -> None:
    session = PromptSession.empty()
    session.source_file = "prompts.md"
    session.current_index = 1
    session.prompts.append(PromptBlock(index=0, label="PROMPT 0", title="Start", content="Inhalt", status="done"))
    session.prompts.append(PromptBlock(index=1, label="PROMPT 1", title="Weiter", content="Naechster Inhalt", status="skipped"))
    target = tmp_path / "session.json"

    save_session(session, target)
    loaded = load_session(target)

    assert loaded.source_file == "prompts.md"
    assert loaded.current_index == 1
    assert loaded.prompts[0].title == "Start"
    assert loaded.prompts[0].content == "Inhalt"
    assert loaded.prompts[0].status == "done"
    assert loaded.prompts[1].status == "skipped"


def test_timestamped_session_uses_sessions_filename_pattern(tmp_path) -> None:
    session = PromptSession.empty()
    session.prompts.append(PromptBlock(index=0, label="PROMPT 0", title="Start", content="Inhalt"))

    target = save_session_as_timestamped_file(session, tmp_path)

    assert target.parent == tmp_path
    assert target.name.startswith(SESSION_FILENAME_PREFIX)
    assert target.name.endswith(".json")
    assert target.stem[: len("session_YYYY-MM-DD_HH-MM-SS")].startswith("session_")
    assert len(target.stem) >= len("session_YYYY-MM-DD_HH-MM-SS")
    assert load_session(target).prompts[0].content == "Inhalt"


def test_session_load_rejects_invalid_json(tmp_path) -> None:
    target = tmp_path / "broken.json"
    target.write_text("{", encoding="utf-8")

    with pytest.raises(SessionError):
        load_session(target)


def test_session_load_rejects_invalid_prompt_status(tmp_path) -> None:
    target = tmp_path / "broken.json"
    target.write_text(
        """
{
  "source_file": "prompts.md",
  "created_at": "2026-01-01T00:00:00+00:00",
  "updated_at": "2026-01-01T00:00:00+00:00",
  "current_index": 0,
  "prompts": [
    {
      "index": 0,
      "label": "PROMPT 0",
      "title": "Start",
      "content": "Inhalt",
      "status": "ungueltig",
      "notes": ""
    }
  ]
}
""",
        encoding="utf-8",
    )

    with pytest.raises(SessionError):
        load_session(target)


def test_session_load_rejects_non_list_prompts(tmp_path) -> None:
    target = tmp_path / "broken.json"
    target.write_text(
        """
{
  "source_file": "prompts.md",
  "created_at": "2026-01-01T00:00:00+00:00",
  "updated_at": "2026-01-01T00:00:00+00:00",
  "current_index": 0,
  "prompts": "not-a-list"
}
""",
        encoding="utf-8",
    )

    with pytest.raises(SessionError):
        load_session(target)


def test_settings_save_and_load_roundtrip(tmp_path) -> None:
    target = tmp_path / "settings.json"
    settings = InjectorSettings(
        last_directory="C:/Prompts",
        always_on_top=True,
        restore_clipboard=False,
        paste_mode="clipboard",
        window_geometry="1200x800+10+20",
        enable_global_hotkeys=True,
    )

    save_settings(settings, target)
    loaded = load_settings(target)

    assert loaded == settings


def test_settings_load_rejects_non_object_json(tmp_path) -> None:
    target = tmp_path / "settings.json"
    target.write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(SettingsError):
        load_settings(target)


def test_settings_string_booleans_are_parsed_explicitly() -> None:
    settings = InjectorSettings.from_dict(
        {
            "restore_clipboard": "false",
            "always_on_top": "true",
        }
    )

    assert settings.restore_clipboard is False
    assert settings.always_on_top is True
