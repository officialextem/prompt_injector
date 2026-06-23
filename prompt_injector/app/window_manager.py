from __future__ import annotations

try:
    import pygetwindow
except ImportError:  # pragma: no cover - wird ueber Tests per Monkeypatch abgedeckt.
    pygetwindow = None


class WindowManagerError(RuntimeError):
    """Fehler beim Lesen oder Fokussieren von Zielfenstern."""


def list_visible_window_titles() -> list[str]:
    if pygetwindow is None:
        raise WindowManagerError("pygetwindow fehlt. Bitte Abhaengigkeiten mit `pip install -r requirements.txt` installieren.")

    try:
        windows = pygetwindow.getAllWindows()
    except Exception as exc:
        raise WindowManagerError(f"Fensterliste konnte nicht gelesen werden: {type(exc).__name__}: {exc}") from exc

    titles: list[str] = []
    for window in windows:
        title = str(getattr(window, "title", "")).strip()
        if title and title not in titles:
            titles.append(title)
    return titles


def focus_window_by_title(title: str) -> None:
    wanted = title.strip()
    if not wanted:
        return
    if pygetwindow is None:
        raise WindowManagerError("pygetwindow fehlt. Bitte Abhaengigkeiten mit `pip install -r requirements.txt` installieren.")

    try:
        candidates = pygetwindow.getWindowsWithTitle(wanted)
    except Exception as exc:
        raise WindowManagerError(f"Zielfenster konnte nicht gesucht werden: {type(exc).__name__}: {exc}") from exc
    if not candidates:
        raise WindowManagerError(f"Zielfenster nicht gefunden: {wanted}")

    window = candidates[0]
    try:
        if getattr(window, "isMinimized", False):
            window.restore()
        window.activate()
    except Exception as exc:
        raise WindowManagerError(f"Zielfenster konnte nicht fokussiert werden: {type(exc).__name__}: {exc}") from exc
