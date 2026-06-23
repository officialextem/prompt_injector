from __future__ import annotations

from prompt_injector.app.gui import PromptInjectorApp
from prompt_injector.app.logging_config import configure_logging


def main() -> None:
    configure_logging()
    app = PromptInjectorApp()
    app.run()


if __name__ == "__main__":
    main()
