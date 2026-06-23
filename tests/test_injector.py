import pytest

from prompt_injector.app import injector


class FakeClipboard:
    class PyperclipException(Exception):
        pass

    def __init__(self, initial: str = "") -> None:
        self.value = initial
        self.history: list[str] = []

    def paste(self) -> str:
        return self.value

    def copy(self, text: str) -> None:
        self.value = text
        self.history.append(text)


class FakePyAutoGui:
    def __init__(self) -> None:
        self.PAUSE = 0
        self.hotkeys: list[tuple[str, ...]] = []
        self.pressed: list[str] = []

    def hotkey(self, *keys: str) -> None:
        self.hotkeys.append(keys)

    def press(self, key: str) -> None:
        self.pressed.append(key)


def test_copy_to_clipboard_uses_pyperclip(monkeypatch) -> None:
    clipboard = FakeClipboard()
    monkeypatch.setattr(injector, "pyperclip", clipboard)

    injector.copy_to_clipboard("Prompt")

    assert clipboard.value == "Prompt"


def test_copy_to_clipboard_rejects_empty_text() -> None:
    with pytest.raises(injector.InjectionError):
        injector.copy_to_clipboard("  ")


def test_paste_into_active_window_restores_original_clipboard(monkeypatch) -> None:
    clipboard = FakeClipboard(initial="geheimer alter Inhalt")
    keyboard = FakePyAutoGui()
    monkeypatch.setattr(injector, "pyperclip", clipboard)
    monkeypatch.setattr(injector, "pyautogui", keyboard)

    injector.paste_into_active_window("Neuer Prompt", restore_clipboard=True)

    assert keyboard.hotkeys == [("ctrl", "v")]
    assert clipboard.value == "geheimer alter Inhalt"
    assert clipboard.history == ["Neuer Prompt", "geheimer alter Inhalt"]


def test_paste_into_active_window_can_keep_prompt_in_clipboard(monkeypatch) -> None:
    clipboard = FakeClipboard(initial="alter Inhalt")
    keyboard = FakePyAutoGui()
    monkeypatch.setattr(injector, "pyperclip", clipboard)
    monkeypatch.setattr(injector, "pyautogui", keyboard)

    injector.paste_into_active_window("Neuer Prompt", restore_clipboard=False)

    assert keyboard.hotkeys == [("ctrl", "v")]
    assert clipboard.value == "Neuer Prompt"
    assert clipboard.history == ["Neuer Prompt"]


def test_paste_into_active_window_auto_send_presses_enter(monkeypatch) -> None:
    clipboard = FakeClipboard(initial="alter Inhalt")
    keyboard = FakePyAutoGui()
    monkeypatch.setattr(injector, "pyperclip", clipboard)
    monkeypatch.setattr(injector, "pyautogui", keyboard)

    injector.paste_into_active_window("Neuer Prompt", restore_clipboard=False, auto_send=True)

    assert keyboard.hotkeys == [("ctrl", "v")]
    assert keyboard.pressed == ["enter"]


def test_paste_into_active_window_reports_missing_target(monkeypatch) -> None:
    clipboard = FakeClipboard(initial="alter Inhalt")
    keyboard = FakePyAutoGui()
    monkeypatch.setattr(injector, "pyperclip", clipboard)
    monkeypatch.setattr(injector, "pyautogui", keyboard)
    monkeypatch.setattr(injector, "focus_window_by_title", lambda _title: (_ for _ in ()).throw(injector.WindowManagerError("nicht gefunden")))

    with pytest.raises(injector.InjectionError, match="nicht gefunden"):
        injector.paste_into_active_window("Neuer Prompt", restore_clipboard=False, target_window_title="Codex")


def test_prompt_injector_returns_failed_result_on_missing_dependency(monkeypatch) -> None:
    monkeypatch.setattr(injector, "pyperclip", None)

    result = injector.PromptInjector().copy_to_clipboard("Prompt")

    assert result.success is False
    assert result.status == "failed"
    assert "pyperclip fehlt" in result.message
