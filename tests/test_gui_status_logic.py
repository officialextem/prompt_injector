from prompt_injector.app.gui import PromptInjectorApp
from prompt_injector.app.injector import InjectionResult
from prompt_injector.app.models import PromptBlock, PromptSession


class FakeInjector:
    def __init__(self, result: InjectionResult) -> None:
        self.result = result

    def paste_into_active_window(
        self,
        _text: str,
        restore_clipboard: bool = True,
        target_window_title: str = "",
        auto_send: bool = False,
    ) -> InjectionResult:
        return self.result

    def copy_to_clipboard(self, _text: str) -> InjectionResult:
        return InjectionResult(True, "copied", "kopiert")


def make_app_with_prompt(status: str = "pending") -> PromptInjectorApp:
    app = PromptInjectorApp()
    app.session = PromptSession.empty()
    app.session.prompts = [
        PromptBlock(index=0, label="PROMPT 0", title="Start", content="Inhalt", status=status)
    ]
    app.session.current_index = 0
    app._refresh_all()
    return app


def test_successful_paste_marks_prompt_done() -> None:
    app = make_app_with_prompt(status="copied")
    app.injector = FakeInjector(InjectionResult(True, "inserted", "eingefuegt"))

    app._finish_active_paste(app.session.prompts[0])

    assert app.session.prompts[0].status == "done"
    app.root.destroy()


def test_status_reset_sets_current_prompt_to_pending() -> None:
    app = make_app_with_prompt(status="skipped")

    app.reset_current_prompt_status()

    assert app.session.prompts[0].status == "pending"
    app.root.destroy()
