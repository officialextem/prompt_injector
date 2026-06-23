from __future__ import annotations

from collections.abc import Callable

try:
    import keyboard
except ImportError:  # pragma: no cover - wird ueber Tests per Monkeypatch abgedeckt.
    keyboard = None


class HotkeyError(RuntimeError):
    """Fehler beim Registrieren oder Freigeben globaler Hotkeys."""


class GlobalHotkeyManager:
    def __init__(self) -> None:
        self._handles: list[object] = []

    @property
    def is_active(self) -> bool:
        return bool(self._handles)

    def register(self, callbacks: dict[str, Callable[[], None]]) -> None:
        if keyboard is None:
            raise HotkeyError("keyboard fehlt. Bitte Abhaengigkeiten mit `pip install -r requirements.txt` installieren.")

        self.unregister()
        try:
            for hotkey, callback in callbacks.items():
                self._handles.append(keyboard.add_hotkey(hotkey, callback, suppress=False))
        except Exception as exc:
            self.unregister()
            raise HotkeyError(f"Globale Hotkeys konnten nicht registriert werden: {type(exc).__name__}: {exc}") from exc

    def unregister(self) -> None:
        if keyboard is None:
            self._handles.clear()
            return

        errors: list[Exception] = []
        for handle in self._handles:
            try:
                keyboard.remove_hotkey(handle)
            except Exception as exc:
                errors.append(exc)
        self._handles.clear()
        if errors:
            first = errors[0]
            raise HotkeyError(f"Globale Hotkeys konnten nicht vollstaendig freigegeben werden: {type(first).__name__}: {first}")
