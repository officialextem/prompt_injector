from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from prompt_injector.app.models import PromptSession


DEFAULT_SESSIONS_DIR = Path(__file__).resolve().parents[1] / "sessions"
SESSION_FILENAME_PREFIX = "session_"


class SessionError(ValueError):
    """Fehler beim Speichern oder Laden einer Prompt-Injector Session."""


def build_session_path(sessions_dir: Path = DEFAULT_SESSIONS_DIR) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_path = sessions_dir / f"{SESSION_FILENAME_PREFIX}{timestamp}.json"
    if not base_path.exists():
        return base_path

    for suffix in range(2, 100):
        candidate = sessions_dir / f"{SESSION_FILENAME_PREFIX}{timestamp}_{suffix:02d}.json"
        if not candidate.exists():
            return candidate
    raise SessionError("Es konnte kein freier Session-Dateiname erzeugt werden.")


def save_session(session: PromptSession, path: Path | None = None) -> Path:
    target_path = path if path is not None else build_session_path()
    if target_path.suffix.lower() != ".json":
        raise SessionError("Sessions muessen als .json gespeichert werden.")
    session.touch()
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(session.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        raise SessionError(f"Session konnte nicht gespeichert werden: {target_path}") from exc
    return target_path


def save_session_as_timestamped_file(
    session: PromptSession,
    sessions_dir: Path = DEFAULT_SESSIONS_DIR,
) -> Path:
    return save_session(session, build_session_path(sessions_dir))


def load_session(path: Path) -> PromptSession:
    if path.suffix.lower() != ".json":
        raise SessionError("Nur .json Sessions koennen geladen werden.")
    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SessionError(f"Session-Datei ist kein gueltiges JSON: {path}") from exc
    except OSError as exc:
        raise SessionError(f"Session konnte nicht gelesen werden: {path}") from exc

    try:
        if not isinstance(raw_data, dict):
            raise SessionError("Session-Datei muss ein JSON-Objekt enthalten.")
        return PromptSession.from_dict(raw_data)
    except (TypeError, ValueError, KeyError) as exc:
        raise SessionError(f"Session-Datei hat eine ungueltige Struktur: {path}") from exc
