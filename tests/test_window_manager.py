import pytest

from prompt_injector.app import window_manager


class FakeWindow:
    def __init__(self, title: str, minimized: bool = False) -> None:
        self.title = title
        self.isMinimized = minimized
        self.restored = False
        self.activated = False

    def restore(self) -> None:
        self.restored = True
        self.isMinimized = False

    def activate(self) -> None:
        self.activated = True


class FakePyGetWindow:
    def __init__(self) -> None:
        self.window = FakeWindow("Codex", minimized=True)

    def getAllWindows(self):
        return [FakeWindow(""), FakeWindow("Codex"), FakeWindow("Codex"), FakeWindow("ChatGPT")]

    def getWindowsWithTitle(self, _title: str):
        return [self.window]


def test_list_visible_window_titles_filters_empty_and_duplicates(monkeypatch) -> None:
    monkeypatch.setattr(window_manager, "pygetwindow", FakePyGetWindow())

    assert window_manager.list_visible_window_titles() == ["Codex", "ChatGPT"]


def test_focus_window_restores_and_activates(monkeypatch) -> None:
    fake = FakePyGetWindow()
    monkeypatch.setattr(window_manager, "pygetwindow", fake)

    window_manager.focus_window_by_title("Codex")

    assert fake.window.restored is True
    assert fake.window.activated is True


def test_focus_window_reports_missing_dependency(monkeypatch) -> None:
    monkeypatch.setattr(window_manager, "pygetwindow", None)

    with pytest.raises(window_manager.WindowManagerError, match="pygetwindow fehlt"):
        window_manager.focus_window_by_title("Codex")
