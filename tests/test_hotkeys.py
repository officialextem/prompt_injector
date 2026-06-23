import pytest

from prompt_injector.app import hotkeys


class FakeKeyboard:
    def __init__(self) -> None:
        self.registered: list[tuple[str, object]] = []
        self.removed: list[object] = []

    def add_hotkey(self, name: str, callback, suppress: bool = False):
        assert suppress is False
        handle = f"handle:{name}"
        self.registered.append((name, handle))
        return handle

    def remove_hotkey(self, handle) -> None:
        self.removed.append(handle)


def test_global_hotkey_manager_registers_and_unregisters(monkeypatch) -> None:
    fake_keyboard = FakeKeyboard()
    monkeypatch.setattr(hotkeys, "keyboard", fake_keyboard)
    manager = hotkeys.GlobalHotkeyManager()

    manager.register({"f6": lambda: None, "f9": lambda: None})

    assert manager.is_active is True
    assert fake_keyboard.registered == [("f6", "handle:f6"), ("f9", "handle:f9")]

    manager.unregister()

    assert manager.is_active is False
    assert fake_keyboard.removed == ["handle:f6", "handle:f9"]


def test_global_hotkey_manager_reports_missing_dependency(monkeypatch) -> None:
    monkeypatch.setattr(hotkeys, "keyboard", None)
    manager = hotkeys.GlobalHotkeyManager()

    with pytest.raises(hotkeys.HotkeyError, match="keyboard fehlt"):
        manager.register({"f6": lambda: None})
