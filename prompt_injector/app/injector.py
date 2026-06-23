from __future__ import annotations

from dataclasses import dataclass

from prompt_injector.app.window_manager import WindowManagerError, focus_window_by_title

try:
    import pyautogui
except ImportError:  # pragma: no cover - wird ueber Tests per Monkeypatch abgedeckt.
    pyautogui = None

try:
    import pyperclip
except ImportError:  # pragma: no cover - wird ueber Tests per Monkeypatch abgedeckt.
    pyperclip = None


PASTE_DELAY_SECONDS = 0.15


class InjectionError(RuntimeError):
    """Fehler bei Clipboard- oder Einfuege-Aktionen."""


@dataclass(slots=True)
class InjectionResult:
    success: bool
    status: str
    message: str


def _require_pyperclip() -> None:
    if pyperclip is None:
        raise InjectionError("pyperclip fehlt. Bitte Abhaengigkeiten mit `pip install -r requirements.txt` installieren.")


def _require_pyautogui() -> None:
    if pyautogui is None:
        raise InjectionError("pyautogui fehlt. Bitte Abhaengigkeiten mit `pip install -r requirements.txt` installieren.")


def _read_clipboard() -> str:
    _require_pyperclip()
    try:
        return str(pyperclip.paste())
    except pyperclip.PyperclipException as exc:
        raise InjectionError("Clipboard konnte nicht gelesen werden.") from exc


def _write_clipboard(text: str) -> None:
    _require_pyperclip()
    try:
        pyperclip.copy(text)
    except pyperclip.PyperclipException as exc:
        raise InjectionError("Clipboard konnte nicht geschrieben werden.") from exc


def copy_to_clipboard(text: str) -> None:
    if not text.strip():
        raise InjectionError("Leerer Prompt wurde nicht in die Zwischenablage kopiert.")
    _write_clipboard(text)


def paste_into_active_window(
    text: str,
    restore_clipboard: bool = True,
    target_window_title: str = "",
    auto_send: bool = False,
) -> None:
    if not text.strip():
        raise InjectionError("Leerer Prompt wurde nicht eingefuegt.")

    _require_pyautogui()
    original_clipboard = _read_clipboard() if restore_clipboard else None
    try:
        if target_window_title.strip():
            try:
                focus_window_by_title(target_window_title)
            except WindowManagerError as exc:
                raise InjectionError(str(exc)) from exc
        _write_clipboard(text)
        pyautogui.PAUSE = PASTE_DELAY_SECONDS
        pyautogui.hotkey("ctrl", "v")
        if auto_send:
            pyautogui.press("enter")
    except InjectionError:
        raise
    except Exception as exc:
        raise InjectionError("Strg+V konnte nicht an das aktive Fenster gesendet werden.") from exc
    finally:
        if restore_clipboard and original_clipboard is not None:
            try:
                _write_clipboard(original_clipboard)
            except InjectionError as exc:
                raise InjectionError("Prompt wurde eingefuegt, aber das Clipboard konnte nicht wiederhergestellt werden.") from exc


class PromptInjector:
    def copy_to_clipboard(self, text: str) -> InjectionResult:
        try:
            copy_to_clipboard(text)
        except InjectionError as exc:
            return InjectionResult(False, "failed", str(exc))
        return InjectionResult(True, "copied", "Prompt wurde in die Zwischenablage kopiert.")

    def paste_into_active_window(
        self,
        text: str,
        restore_clipboard: bool = True,
        target_window_title: str = "",
        auto_send: bool = False,
    ) -> InjectionResult:
        try:
            paste_into_active_window(
                text,
                restore_clipboard=restore_clipboard,
                target_window_title=target_window_title,
                auto_send=auto_send,
            )
        except InjectionError as exc:
            return InjectionResult(False, "failed", str(exc))

        restore_hint = " Clipboard wurde wiederhergestellt." if restore_clipboard else ""
        send_hint = " Enter wurde gesendet." if auto_send else ""
        return InjectionResult(
            True,
            "inserted",
            f"Prompt wurde per Strg+V eingefuegt.{send_hint}{restore_hint}",
        )
