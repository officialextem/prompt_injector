from __future__ import annotations

import json
from pathlib import Path

from prompt_injector.app.models import InjectorSettings


DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parents[1] / "settings.json"


class SettingsError(ValueError):
    """Fehler beim Laden oder Speichern der lokalen Einstellungen."""


def load_settings(path: Path = DEFAULT_SETTINGS_PATH) -> InjectorSettings:
    if not path.exists():
        settings = InjectorSettings()
        save_settings(settings, path)
        return settings

    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SettingsError(f"Einstellungsdatei ist kein gueltiges JSON: {path}") from exc
    except OSError as exc:
        raise SettingsError(f"Einstellungsdatei konnte nicht gelesen werden: {path}") from exc

    if not isinstance(raw_data, dict):
        raise SettingsError(f"Einstellungsdatei muss ein JSON-Objekt enthalten: {path}")
    return InjectorSettings.from_dict(raw_data)


def save_settings(settings: InjectorSettings, path: Path = DEFAULT_SETTINGS_PATH) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        raise SettingsError(f"Einstellungen konnten nicht gespeichert werden: {path}") from exc
