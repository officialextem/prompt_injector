from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


PROMPT_STATUSES = {"pending", "copied", "inserted", "done", "skipped", "failed"}
DEFAULT_HOTKEYS = {
    "copy": "f6",
    "paste": "f7",
    "done_next": "f8",
    "stop": "f9",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class PromptBlock:
    index: int
    label: str
    title: str
    content: str
    status: str = "pending"
    notes: str = ""

    def __post_init__(self) -> None:
        if self.status not in PROMPT_STATUSES:
            raise ValueError(f"Ungueltiger Prompt-Status: {self.status}")

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "label": self.label,
            "title": self.title,
            "content": self.content,
            "status": self.status,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "PromptBlock":
        return cls(
            index=int(data.get("index", 0)),
            label=str(data.get("label", "")),
            title=str(data.get("title", "")),
            content=str(data.get("content", "")),
            status=str(data.get("status", "pending")),
            notes=str(data.get("notes", "")),
        )


@dataclass(slots=True)
class PromptSession:
    source_file: str
    created_at: str
    updated_at: str
    current_index: int
    prompts: list[PromptBlock] = field(default_factory=list)

    @classmethod
    def empty(cls) -> "PromptSession":
        now = utc_now_iso()
        return cls(source_file="", created_at=now, updated_at=now, current_index=0, prompts=[])

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, object]:
        return {
            "source_file": self.source_file,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_index": self.current_index,
            "prompts": [prompt.to_dict() for prompt in self.prompts],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "PromptSession":
        raw_prompts = data.get("prompts", [])
        if not isinstance(raw_prompts, list):
            raise ValueError("Session-Feld `prompts` muss eine Liste sein.")
        prompts = [PromptBlock.from_dict(item) for item in raw_prompts if isinstance(item, dict)]
        max_index = max(len(prompts) - 1, 0)
        current_index = max(0, min(int(data.get("current_index", 0)), max_index))
        return cls(
            source_file=str(data.get("source_file", "")),
            created_at=str(data.get("created_at", utc_now_iso())),
            updated_at=str(data.get("updated_at", utc_now_iso())),
            current_index=current_index,
            prompts=prompts,
        )


@dataclass(slots=True)
class InjectorSettings:
    last_directory: str = ""
    restore_clipboard: bool = True
    paste_mode: str = "clipboard"
    always_on_top: bool = False
    window_geometry: str = "1180x760"
    enable_global_hotkeys: bool = False
    target_window_title: str = ""
    auto_send_after_paste: bool = False
    hotkeys: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_HOTKEYS))

    def to_dict(self) -> dict[str, object]:
        return {
            "last_directory": self.last_directory,
            "restore_clipboard": self.restore_clipboard,
            "paste_mode": self.paste_mode,
            "always_on_top": self.always_on_top,
            "window_geometry": self.window_geometry,
            "enable_global_hotkeys": self.enable_global_hotkeys,
            "target_window_title": self.target_window_title,
            "auto_send_after_paste": self.auto_send_after_paste,
            "hotkeys": dict(self.hotkeys),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "InjectorSettings":
        return cls(
            last_directory=str(data.get("last_directory", "")),
            restore_clipboard=_coerce_bool(data.get("restore_clipboard", True), True),
            paste_mode=str(data.get("paste_mode", "clipboard")),
            always_on_top=_coerce_bool(data.get("always_on_top", False), False),
            window_geometry=str(data.get("window_geometry", "1180x760")),
            enable_global_hotkeys=_coerce_bool(data.get("enable_global_hotkeys", False), False),
            target_window_title=str(data.get("target_window_title", "")),
            auto_send_after_paste=_coerce_bool(data.get("auto_send_after_paste", False), False),
            hotkeys=_coerce_hotkeys(data.get("hotkeys", {})),
        )


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "ja"}:
            return True
        if normalized in {"false", "0", "no", "nein"}:
            return False
    return default


def _coerce_hotkeys(value: Any) -> dict[str, str]:
    hotkeys = dict(DEFAULT_HOTKEYS)
    if not isinstance(value, dict):
        return hotkeys

    used: set[str] = set()
    for action, default_hotkey in DEFAULT_HOTKEYS.items():
        raw_value = value.get(action, default_hotkey)
        hotkey = str(raw_value).strip().lower()
        if not hotkey or hotkey in used:
            hotkey = default_hotkey
        hotkeys[action] = hotkey
        used.add(hotkey)
    return hotkeys
