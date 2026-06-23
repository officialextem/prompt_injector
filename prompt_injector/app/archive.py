from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from prompt_injector.app.models import PromptBlock, PromptSession


DEFAULT_RUNS_DIR = Path(__file__).resolve().parents[1] / "runs"


class ArchiveError(ValueError):
    """Fehler beim manuellen Antwort-Archiv."""


@dataclass(slots=True)
class ArchiveResult:
    run_dir: Path
    prompt_file: Path
    response_file: Path
    summary_file: Path


def save_manual_response(
    session: PromptSession,
    prompt: PromptBlock,
    response_text: str,
    current_session_file: Path | None,
    runs_dir: Path = DEFAULT_RUNS_DIR,
) -> ArchiveResult:
    if not response_text.strip():
        raise ArchiveError("Leere Antworten werden nicht archiviert.")

    run_dir = _resolve_run_dir(session, current_session_file, runs_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    prompt_file = run_dir / f"prompt_{prompt.index:02d}.md"
    response_file = run_dir / f"response_{prompt.index:02d}.md"
    summary_file = run_dir / "summary.json"

    prompt_file.write_text(_format_prompt(prompt), encoding="utf-8")
    response_file.write_text(response_text.strip() + "\n", encoding="utf-8")
    _write_summary(summary_file, session, current_session_file, run_dir)

    return ArchiveResult(
        run_dir=run_dir,
        prompt_file=prompt_file,
        response_file=response_file,
        summary_file=summary_file,
    )


def _resolve_run_dir(
    session: PromptSession,
    current_session_file: Path | None,
    runs_dir: Path,
) -> Path:
    if current_session_file is not None:
        return runs_dir / current_session_file.stem
    source = Path(session.source_file).stem if session.source_file else "unsaved_session"
    return runs_dir / f"{_safe_name(source)}_{_session_timestamp(session.created_at)}"


def _format_prompt(prompt: PromptBlock) -> str:
    return "\n".join(
        [
            f"# {prompt.label}: {prompt.title}",
            "",
            f"- Index: {prompt.index}",
            f"- Status: {prompt.status}",
            "",
            "## Prompt",
            "",
            prompt.content.rstrip(),
            "",
        ]
    )


def _write_summary(
    summary_file: Path,
    session: PromptSession,
    current_session_file: Path | None,
    run_dir: Path,
) -> None:
    response_files = sorted(path.name for path in run_dir.glob("response_*.md"))
    prompt_status = [
        {
            "index": prompt.index,
            "label": prompt.label,
            "title": prompt.title,
            "status": prompt.status,
        }
        for prompt in session.prompts
    ]
    summary = {
        "session_file": str(current_session_file) if current_session_file else "",
        "source_file": session.source_file,
        "prompt_count": len(session.prompts),
        "prompt_status": prompt_status,
        "response_files": response_files,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def _safe_name(value: str) -> str:
    safe = "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in value)
    return safe.strip("_") or "run"


def _session_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        parsed = datetime.now(timezone.utc)
    return parsed.strftime("%Y-%m-%d_%H-%M-%S")
