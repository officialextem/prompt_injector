from __future__ import annotations

import logging
from pathlib import Path


RUNS_DIR = Path(__file__).resolve().parents[1] / "runs"


def configure_logging(log_dir: Path = RUNS_DIR) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "prompt_injector.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
