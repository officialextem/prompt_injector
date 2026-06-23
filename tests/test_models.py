import pytest

from prompt_injector.app.models import InjectorSettings, PromptBlock, PromptSession


def test_prompt_block_rejects_unknown_status() -> None:
    with pytest.raises(ValueError):
        PromptBlock(index=0, label="PROMPT 0", title="PROMPT 0", content="Text", status="unknown")


def test_prompt_session_roundtrip_clamps_current_index() -> None:
    session = PromptSession.from_dict(
        {
            "source_file": "input.md",
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "current_index": 99,
            "prompts": [{"index": 0, "label": "PROMPT 0", "title": "PROMPT 0", "content": "Text"}],
        }
    )

    assert session.current_index == 0
    assert session.prompts[0].status == "pending"


def test_injector_settings_roundtrip() -> None:
    settings = InjectorSettings(
        last_directory="C:/Prompts",
        always_on_top=True,
        window_geometry="1200x800+10+20",
        enable_global_hotkeys=True,
        target_window_title="Codex",
        auto_send_after_paste=True,
        hotkeys={"copy": "ctrl+shift+c", "paste": "ctrl+shift+v", "done_next": "f10", "stop": "f12"},
    )

    assert InjectorSettings.from_dict(settings.to_dict()) == settings


def test_injector_settings_defaults_for_old_settings() -> None:
    settings = InjectorSettings.from_dict({})

    assert settings.target_window_title == ""
    assert settings.auto_send_after_paste is False
    assert settings.hotkeys == {"copy": "f6", "paste": "f7", "done_next": "f8", "stop": "f9"}


def test_injector_settings_replaces_empty_or_duplicate_hotkeys() -> None:
    settings = InjectorSettings.from_dict(
        {
            "hotkeys": {
                "copy": "",
                "paste": "f7",
                "done_next": "f7",
                "stop": "f9",
            }
        }
    )

    assert settings.hotkeys["copy"] == "f6"
    assert settings.hotkeys["paste"] == "f7"
    assert settings.hotkeys["done_next"] == "f8"
    assert settings.hotkeys["stop"] == "f9"
