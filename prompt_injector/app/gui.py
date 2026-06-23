from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from prompt_injector.app.archive import ArchiveError, save_manual_response
from prompt_injector.app.fixing_prompt import FIXING_PROMPT
from prompt_injector.app.hotkeys import GlobalHotkeyManager, HotkeyError
from prompt_injector.app.injector import PromptInjector
from prompt_injector.app.models import InjectorSettings, PromptBlock, PromptSession
from prompt_injector.app.parser import ParserError, estimate_tokens, load_prompt_blocks
from prompt_injector.app.session_manager import DEFAULT_SESSIONS_DIR, SessionError, load_session, save_session_as_timestamped_file
from prompt_injector.app.settings import SettingsError, load_settings, save_settings
from prompt_injector.app.window_manager import WindowManagerError, list_visible_window_titles


LOGGER = logging.getLogger(__name__)
APP_TITLE = "Prompt-Injector"


class Tooltip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        self.widget.bind("<Enter>", self._show)
        self.widget.bind("<Leave>", self._hide)
        self.widget.bind("<ButtonPress>", self._hide)

    def _show(self, _event: tk.Event) -> None:
        if self.tip_window is not None or not self.text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tip_window,
            text=self.text,
            bg="#2b2b37",
            fg="#f4f4f7",
            relief=tk.SOLID,
            borderwidth=1,
            padx=8,
            pady=4,
        )
        label.pack()

    def _hide(self, _event: tk.Event | None = None) -> None:
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


class PromptInjectorApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.minsize(760, 520)

        self.session = PromptSession.empty()
        self.settings = self._load_settings_safely()
        self.current_session_file: Path | None = None
        self.injector = PromptInjector()
        self.hotkeys = GlobalHotkeyManager()
        self.global_hotkeys_var = tk.BooleanVar(value=self.settings.enable_global_hotkeys)
        self._is_refreshing = False
        self._has_unsaved_changes = False
        self._pending_paste_after_id: str | None = None

        self._apply_window_geometry()
        self.root.attributes("-topmost", self.settings.always_on_top)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_style()
        self._build_layout()
        self._refresh_all()
        if self.settings.enable_global_hotkeys:
            if not self._enable_global_hotkeys(show_errors=False):
                self.settings.enable_global_hotkeys = False
                self.global_hotkeys_var.set(False)
                self._save_settings_safely()
        LOGGER.info("App gestartet")

    def run(self) -> None:
        self.root.mainloop()

    def _load_settings_safely(self) -> InjectorSettings:
        try:
            return load_settings()
        except SettingsError as exc:
            LOGGER.exception("Settings konnten nicht geladen werden: %s: %s", type(exc).__name__, exc)
            messagebox.showwarning(APP_TITLE, str(exc))
            return InjectorSettings()

    def _apply_window_geometry(self) -> None:
        try:
            self.root.geometry(self.settings.window_geometry)
        except tk.TclError as exc:
            LOGGER.exception("Fenstergeometrie ungueltig: %s: %s", type(exc).__name__, exc)
            self.settings.window_geometry = InjectorSettings().window_geometry
            self.root.geometry(self.settings.window_geometry)
            self._save_settings_safely()

    def _build_style(self) -> None:
        self.root.configure(bg="#15151b")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Root.TFrame", background="#15151b")
        style.configure("Panel.TFrame", background="#20202a")
        style.configure("TLabel", background="#15151b", foreground="#f4f4f7")
        style.configure("Panel.TLabel", background="#20202a", foreground="#f4f4f7")
        style.configure("Muted.TLabel", background="#15151b", foreground="#a7a7b5")
        style.configure("TButton", background="#6d4aff", foreground="#ffffff", padding=(10, 6))
        style.map("TButton", background=[("active", "#22d3ee")], foreground=[("active", "#101014")])
        style.configure("Treeview", background="#20202a", fieldbackground="#20202a", foreground="#f4f4f7")
        style.configure("Treeview.Heading", background="#2b2b37", foreground="#ffffff")
        style.configure("Header.TFrame", background="#15151b")

    def _build_layout(self) -> None:
        root_frame = ttk.Frame(self.root, style="Root.TFrame", padding=14)
        root_frame.pack(fill=tk.BOTH, expand=True)
        root_frame.grid_rowconfigure(0, weight=0)
        root_frame.grid_rowconfigure(1, weight=1)
        root_frame.grid_rowconfigure(2, weight=0)
        root_frame.grid_rowconfigure(3, weight=0)
        root_frame.grid_columnconfigure(0, weight=1)

        header = ttk.Frame(root_frame, style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(header, text=APP_TITLE).pack(side=tk.LEFT)

        header_actions = ttk.Frame(header, style="Header.TFrame")
        header_actions.pack(side=tk.RIGHT)
        self.load_file_button = ttk.Button(header_actions, text="📂", width=3, command=self.load_prompt_file)
        self.load_file_button.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(self.load_file_button, "Datei laden")
        self.load_session_button = ttk.Button(header_actions, text="⇩", width=3, command=self.load_session_file)
        self.load_session_button.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(self.load_session_button, "Session laden")
        self.save_session_button = ttk.Button(header_actions, text="💾", width=3, command=self.save_session_file)
        self.save_session_button.pack(side=tk.LEFT, padx=(0, 10))
        Tooltip(self.save_session_button, "Session speichern")
        self.fixing_prompt_button = ttk.Button(header_actions, text="🧹", width=3, command=self.copy_fixing_prompt)
        self.fixing_prompt_button.pack(side=tk.LEFT, padx=(0, 6))
        Tooltip(self.fixing_prompt_button, "Fixing-Prompt kopieren")
        self.settings_button = ttk.Button(header_actions, text="⚙", width=3, command=self.open_settings_dialog)
        self.settings_button.pack(side=tk.LEFT)
        Tooltip(self.settings_button, "Settings")

        body = ttk.Frame(root_frame, style="Root.TFrame")
        body.grid(row=1, column=0, sticky="nsew")

        left = ttk.Frame(body, style="Panel.TFrame", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))

        ttk.Label(left, text="Einfuege-Modus: Clipboard", style="Panel.TLabel").pack(anchor=tk.W, pady=(0, 12))

        ttk.Label(left, text="Prompts", style="Panel.TLabel").pack(anchor=tk.W)
        self.prompt_tree = ttk.Treeview(left, columns=("status",), show="tree headings", height=25)
        self.prompt_tree.heading("#0", text="Prompt")
        self.prompt_tree.heading("status", text="Status")
        self.prompt_tree.column("#0", width=260, stretch=False)
        self.prompt_tree.column("status", width=90, anchor=tk.CENTER, stretch=False)
        self.prompt_tree.pack(fill=tk.BOTH, expand=True, pady=(8, 8))
        self.prompt_tree.bind("<<TreeviewSelect>>", self._on_prompt_selected)

        self.progress_var = tk.StringVar(value="0 / 0")
        ttk.Label(left, textvariable=self.progress_var, style="Panel.TLabel").pack(anchor=tk.W)
        self.session_file_var = tk.StringVar(value="Session: nicht gespeichert")
        ttk.Label(left, textvariable=self.session_file_var, style="Panel.TLabel", wraplength=340).pack(anchor=tk.W, pady=(8, 0))

        right = ttk.Frame(body, style="Root.TFrame")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(right)
        notebook.pack(fill=tk.BOTH, expand=True)
        prompt_tab = ttk.Frame(notebook, style="Root.TFrame", padding=(0, 0, 0, 4))
        response_tab = ttk.Frame(notebook, style="Root.TFrame", padding=(0, 0, 0, 4))
        notebook.add(prompt_tab, text="Prompt")
        notebook.add(response_tab, text="Antwort-Archiv")

        self.prompt_number_var = tk.StringVar(value="Kein Prompt geladen")
        ttk.Label(prompt_tab, textvariable=self.prompt_number_var).pack(anchor=tk.W)

        ttk.Label(prompt_tab, text="Prompt-Titel").pack(anchor=tk.W, pady=(10, 3))
        self.title_var = tk.StringVar()
        self.title_entry = tk.Entry(
            prompt_tab,
            textvariable=self.title_var,
            bg="#20202a",
            fg="#f4f4f7",
            insertbackground="#22d3ee",
            relief=tk.FLAT,
        )
        self.title_entry.pack(fill=tk.X)
        self.title_entry.bind("<KeyRelease>", self._on_editor_changed)
        self.title_entry.bind("<FocusOut>", self._on_editor_changed)

        ttk.Label(prompt_tab, text="Prompt-Inhalt").pack(anchor=tk.W, pady=(12, 3))
        self.content_text = tk.Text(
            prompt_tab,
            wrap=tk.WORD,
            undo=True,
            bg="#20202a",
            fg="#f4f4f7",
            insertbackground="#22d3ee",
            selectbackground="#6d4aff",
            relief=tk.FLAT,
            padx=10,
            pady=10,
            font=("Consolas", 11),
        )
        self.content_text.pack(fill=tk.BOTH, expand=True)
        self.content_text.bind("<<Modified>>", self._on_text_modified)

        self.count_var = tk.StringVar(value="Zeichen: 0 | Token grob: 0")
        ttk.Label(prompt_tab, textvariable=self.count_var, style="Muted.TLabel").pack(anchor=tk.W, pady=(8, 0))

        ttk.Label(response_tab, text="Antwort-Archiv (manuell einfuegen)").pack(anchor=tk.W, pady=(0, 3))
        self.response_text = tk.Text(
            response_tab,
            height=12,
            wrap=tk.WORD,
            undo=True,
            bg="#20202a",
            fg="#f4f4f7",
            insertbackground="#22d3ee",
            selectbackground="#6d4aff",
            relief=tk.FLAT,
            padx=10,
            pady=10,
            font=("Consolas", 10),
        )
        self.response_text.pack(fill=tk.BOTH, expand=True)

        controls = ttk.Frame(root_frame, style="Root.TFrame")
        controls.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        for column in range(8):
            controls.grid_columnconfigure(column, weight=1, uniform="controls")
        self.previous_button = ttk.Button(controls, text="←", width=3, command=self.previous_prompt)
        self.previous_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        Tooltip(self.previous_button, "Zurueck")
        self.next_button = ttk.Button(controls, text="→", width=3, command=self.next_prompt)
        self.next_button.grid(row=0, column=1, sticky="ew", padx=4)
        Tooltip(self.next_button, "Weiter")
        self.copy_button = ttk.Button(controls, text="📋", width=3, command=self.copy_current_prompt)
        self.copy_button.grid(row=0, column=2, sticky="ew", padx=4)
        Tooltip(self.copy_button, "In Clipboard kopieren")
        self.paste_button = ttk.Button(controls, text="📥", width=3, command=self.paste_current_prompt)
        self.paste_button.grid(row=0, column=3, sticky="ew", padx=4)
        Tooltip(self.paste_button, "In aktives oder gewaehltes Fenster einfuegen")
        self.done_button = ttk.Button(controls, text="✓", width=3, command=self.mark_done)
        self.done_button.grid(row=0, column=4, sticky="ew", padx=4)
        Tooltip(self.done_button, "Als erledigt markieren")
        self.skip_button = ttk.Button(controls, text="⏭", width=3, command=self.mark_skipped)
        self.skip_button.grid(row=0, column=5, sticky="ew", padx=4)
        Tooltip(self.skip_button, "Ueberspringen")
        self.reset_status_button = ttk.Button(controls, text="↺", width=3, command=self.reset_current_prompt_status)
        self.reset_status_button.grid(row=0, column=6, sticky="ew", padx=4)
        Tooltip(self.reset_status_button, "Status zuruecksetzen")
        self.save_response_button = ttk.Button(controls, text="💾", width=3, command=self.save_current_response)
        self.save_response_button.grid(row=0, column=7, sticky="ew", padx=(4, 0))
        Tooltip(self.save_response_button, "Antwort speichern")

        self.status_var = tk.StringVar(value="Bereit")
        ttk.Label(root_frame, textvariable=self.status_var, style="Muted.TLabel").grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(10, 0),
        )

    def load_prompt_file(self) -> None:
        if not self._confirm_unsaved_changes():
            return
        initial_dir = self.settings.last_directory or str(Path.home())
        path_text = filedialog.askopenfilename(
            title="Prompt-Datei laden",
            initialdir=initial_dir,
            filetypes=[
                ("Prompt-Dateien", "*.txt *.md *.pdf"),
                ("Textdateien", "*.txt"),
                ("Markdown", "*.md"),
                ("PDF", "*.pdf"),
            ],
        )
        if not path_text:
            return

        path = Path(path_text)
        try:
            prompts = load_prompt_blocks(path)
        except ParserError as exc:
            LOGGER.exception("Datei konnte nicht geladen werden: %s: %s", type(exc).__name__, exc)
            messagebox.showerror(APP_TITLE, str(exc))
            return

        self._save_settings_last_directory(path.parent)
        self.session = PromptSession.empty()
        self.session.source_file = str(path)
        self.session.prompts = prompts
        self.session.current_index = 0
        self.session.touch()
        self.current_session_file = None
        self._has_unsaved_changes = True
        self._refresh_all()
        self._set_status(f"Datei geladen: {path.name} | Prompts erkannt: {len(prompts)}")
        LOGGER.info("Datei geladen: %s", path)
        LOGGER.info("Anzahl erkannter Prompts: %s", len(prompts))

    def load_session_file(self) -> None:
        if not self._confirm_unsaved_changes():
            return
        initial_dir = self.settings.last_directory or str(DEFAULT_SESSIONS_DIR)
        path_text = filedialog.askopenfilename(
            title="Session laden",
            initialdir=initial_dir,
            filetypes=[("Prompt-Injector Session", "*.json")],
        )
        if not path_text:
            return

        path = Path(path_text)
        try:
            self.session = load_session(path)
        except SessionError as exc:
            LOGGER.exception("Session konnte nicht geladen werden: %s: %s", type(exc).__name__, exc)
            messagebox.showerror(APP_TITLE, str(exc))
            return

        self._save_settings_last_directory(path.parent)
        self.current_session_file = path
        self._has_unsaved_changes = False
        self._refresh_all()
        self._set_status(f"Session geladen: {path.name}")
        LOGGER.info("Session geladen: %s", path)

    def save_session_file(self) -> bool:
        self._save_current_prompt()
        try:
            path = save_session_as_timestamped_file(self.session)
        except SessionError as exc:
            LOGGER.exception("Session konnte nicht gespeichert werden: %s: %s", type(exc).__name__, exc)
            messagebox.showerror(APP_TITLE, str(exc))
            return False

        self._save_settings_last_directory(DEFAULT_SESSIONS_DIR)
        self.current_session_file = path
        self._has_unsaved_changes = False
        self._refresh_session_file_label()
        self._refresh_button_states()
        self._set_status(f"Session gespeichert: {path}")
        LOGGER.info("Session gespeichert: %s", path)
        return True

    def copy_current_prompt(self) -> None:
        prompt = self._save_current_prompt()
        if prompt is None:
            self._show_no_prompt_message()
            return
        result = self.injector.copy_to_clipboard(prompt.content)
        prompt.status = result.status
        self.session.touch()
        self._has_unsaved_changes = True
        self._refresh_prompt_list()
        self._refresh_button_states()
        self._set_status(result.message)
        LOGGER.info("Prompt kopiert: index=%s title=%s status=%s", prompt.index, prompt.title, result.status)
        if not result.success:
            LOGGER.error("Prompt kopieren fehlgeschlagen: index=%s title=%s message=%s", prompt.index, prompt.title, result.message)
            messagebox.showwarning(APP_TITLE, result.message)

    def copy_fixing_prompt(self) -> None:
        result = self.injector.copy_to_clipboard(FIXING_PROMPT)
        self._set_status(result.message if not result.success else "Fixing-Prompt wurde in die Zwischenablage kopiert.")
        if result.success:
            LOGGER.info("Fixing-Prompt kopiert")
            return
        LOGGER.error("Fehler beim Kopieren des Fixing-Prompts: %s", result.message)
        messagebox.showwarning(APP_TITLE, result.message)

    def paste_current_prompt(self) -> None:
        prompt = self._save_current_prompt()
        if prompt is None:
            self._show_no_prompt_message()
            return
        if not prompt.content.strip():
            messagebox.showwarning(APP_TITLE, "Leerer Prompt wird nicht eingefuegt.")
            return

        confirmed = messagebox.askyesno(
            APP_TITLE,
            "Der aktuelle Prompt wird in die Zwischenablage kopiert.\n"
            "Nach OK hast du kurz Zeit, das Zielfenster zu fokussieren.\n\n"
            "Prompt-Injector sendet nur Strg+V. Kein Enter, kein Senden-Klick.",
        )
        if not confirmed:
            return

        self.root.iconify()
        self._set_status("Zielfenster fokussieren. In 1,2 Sekunden wird nur Strg+V gesendet.")
        self._pending_paste_after_id = self.root.after(1200, lambda: self._finish_active_paste(prompt))

    def mark_done(self) -> None:
        prompt = self._save_current_prompt()
        if prompt is None:
            self._show_no_prompt_message()
            return
        prompt.status = "done"
        self.session.touch()
        self._has_unsaved_changes = True
        self._refresh_prompt_list()
        self._refresh_button_states()
        self._set_status(f"{prompt.label} als erledigt markiert.")
        LOGGER.info("Prompt erledigt: index=%s title=%s", prompt.index, prompt.title)

    def mark_skipped(self) -> None:
        prompt = self._save_current_prompt()
        if prompt is None:
            self._show_no_prompt_message()
            return
        prompt.status = "skipped"
        self.session.touch()
        self._has_unsaved_changes = True
        self._refresh_prompt_list()
        self._refresh_button_states()
        self._set_status(f"{prompt.label} uebersprungen.")
        LOGGER.info("Prompt uebersprungen: index=%s title=%s", prompt.index, prompt.title)

    def reset_current_prompt_status(self) -> None:
        prompt = self._save_current_prompt()
        if prompt is None:
            self._show_no_prompt_message()
            return
        previous_status = prompt.status
        prompt.status = "pending"
        self.session.touch()
        self._has_unsaved_changes = True
        self._refresh_prompt_list()
        self._refresh_progress()
        self._refresh_button_states()
        self._set_status(f"{prompt.label} wurde auf pending zurueckgesetzt.")
        LOGGER.info(
            "Status zurueckgesetzt: index=%s title=%s previous_status=%s",
            prompt.index,
            prompt.title,
            previous_status,
        )

    def save_current_response(self) -> None:
        prompt = self._save_current_prompt()
        if prompt is None:
            self._show_no_prompt_message()
            return

        response = self.response_text.get("1.0", tk.END).strip()
        try:
            result = save_manual_response(
                self.session,
                prompt,
                response,
                self.current_session_file,
            )
        except ArchiveError as exc:
            LOGGER.exception("Antwort konnte nicht archiviert werden: %s: %s", type(exc).__name__, exc)
            messagebox.showwarning(APP_TITLE, str(exc))
            return

        self.response_text.delete("1.0", tk.END)
        self._set_status(f"Antwort archiviert: {result.response_file}")
        LOGGER.info("Antwort archiviert: prompt_index=%s title=%s file=%s", prompt.index, prompt.title, result.response_file)

    def mark_done_and_prepare_next(self) -> None:
        prompt = self._save_current_prompt()
        if prompt is None:
            self._show_no_prompt_message()
            return
        prompt.status = "done"
        self.session.touch()
        self._has_unsaved_changes = True
        if self.session.current_index < len(self.session.prompts) - 1:
            self.session.current_index += 1
            self._refresh_all()
            self._set_status(f"{prompt.label} als erledigt markiert. Naechster Prompt vorbereitet.")
        else:
            self._refresh_prompt_list()
            self._refresh_button_states()
            self._set_status(f"{prompt.label} als erledigt markiert. Ende der Liste erreicht.")
        LOGGER.info("Prompt erledigt per Hotkey: index=%s title=%s", prompt.index, prompt.title)

    def previous_prompt(self) -> None:
        if not self.session.prompts:
            self._show_no_prompt_message()
            return
        self._save_current_prompt()
        self.session.current_index = max(0, self.session.current_index - 1)
        self.session.touch()
        self._refresh_all()

    def next_prompt(self) -> None:
        if not self.session.prompts:
            self._show_no_prompt_message()
            return
        self._save_current_prompt()
        self.session.current_index = min(len(self.session.prompts) - 1, self.session.current_index + 1)
        self.session.touch()
        self._refresh_all()

    def _finish_active_paste(self, prompt: PromptBlock) -> None:
        self._pending_paste_after_id = None
        result = self.injector.paste_into_active_window(
            prompt.content,
            restore_clipboard=self.settings.restore_clipboard,
            target_window_title=self.settings.target_window_title,
            auto_send=self.settings.auto_send_after_paste,
        )
        prompt.status = "done" if result.success else result.status
        self.session.touch()
        self._has_unsaved_changes = True
        self.root.deiconify()
        self._refresh_prompt_list()
        self._refresh_progress()
        self._refresh_button_states()
        if result.success:
            self._set_status("Prompt wurde eingefuegt und als erledigt markiert.")
            LOGGER.info("Prompt nach Einfuegen als done markiert: index=%s title=%s", prompt.index, prompt.title)
        else:
            self._set_status(result.message)
        if not result.success:
            LOGGER.error("Prompt einfuegen fehlgeschlagen: index=%s title=%s message=%s", prompt.index, prompt.title, result.message)
            messagebox.showwarning(APP_TITLE, result.message)

    def _on_prompt_selected(self, _event: tk.Event) -> None:
        if self._is_refreshing:
            return
        selected = self.prompt_tree.selection()
        if not selected:
            return
        self._save_current_prompt()
        self.session.current_index = int(selected[0])
        self.session.touch()
        self._refresh_editor()
        self._refresh_progress()

    def _on_editor_changed(self, _event: tk.Event) -> None:
        if self._is_refreshing:
            return
        self._save_current_prompt()
        self._refresh_counts()
        self._is_refreshing = True
        try:
            self._refresh_prompt_list()
        finally:
            self._is_refreshing = False

    def _on_text_modified(self, _event: tk.Event) -> None:
        if self._is_refreshing:
            return
        if self.content_text.edit_modified():
            self.content_text.edit_modified(False)
            self._save_current_prompt()
            self._refresh_counts()

    def _current_prompt(self) -> PromptBlock | None:
        if not self.session.prompts:
            return None
        self.session.current_index = max(0, min(self.session.current_index, len(self.session.prompts) - 1))
        return self.session.prompts[self.session.current_index]

    def _save_current_prompt(self) -> PromptBlock | None:
        prompt = self._current_prompt()
        if prompt is None:
            return None
        title = self.title_var.get().strip() or prompt.label
        content = self.content_text.get("1.0", tk.END).strip()
        if prompt.title != title or prompt.content != content:
            prompt.title = title
            prompt.content = content
            self.session.touch()
            self._has_unsaved_changes = True
        return prompt

    def _refresh_all(self) -> None:
        self._is_refreshing = True
        try:
            self._refresh_prompt_list()
            self._refresh_editor()
            self._refresh_progress()
            self._refresh_session_file_label()
            self._refresh_button_states()
        finally:
            self._is_refreshing = False

    def _refresh_prompt_list(self) -> None:
        selected_index = str(self.session.current_index) if self.session.prompts else ""
        self.prompt_tree.delete(*self.prompt_tree.get_children())
        for position, prompt in enumerate(self.session.prompts):
            title = prompt.title if prompt.title else prompt.label
            self.prompt_tree.insert("", tk.END, iid=str(position), text=f"{prompt.label} - {title}", values=(prompt.status,))
        if selected_index and self.prompt_tree.exists(selected_index):
            self.prompt_tree.selection_set(selected_index)
            self.prompt_tree.focus(selected_index)

    def _refresh_editor(self) -> None:
        prompt = self._current_prompt()
        self.content_text.delete("1.0", tk.END)
        self.response_text.delete("1.0", tk.END)
        if prompt is None:
            self.prompt_number_var.set("Kein Prompt geladen")
            self.title_var.set("")
            self._refresh_counts()
            return
        self.prompt_number_var.set(f"{prompt.label} ({self.session.current_index + 1} / {len(self.session.prompts)})")
        self.title_var.set(prompt.title)
        self.content_text.insert("1.0", prompt.content)
        self.content_text.edit_modified(False)
        self._refresh_counts()

    def _refresh_progress(self) -> None:
        total = len(self.session.prompts)
        current = self.session.current_index + 1 if total else 0
        done = sum(1 for prompt in self.session.prompts if prompt.status == "done")
        skipped = sum(1 for prompt in self.session.prompts if prompt.status == "skipped")
        self.progress_var.set(f"{current} / {total} | erledigt: {done} | uebersprungen: {skipped}")

    def _refresh_counts(self) -> None:
        content = self.content_text.get("1.0", tk.END).strip()
        self.count_var.set(f"Zeichen: {len(content)} | Token grob: {estimate_tokens(content)}")

    def _save_settings_last_directory(self, directory: Path) -> None:
        self.settings.last_directory = str(directory)
        self._save_settings_safely()

    def _set_status(self, message: str) -> None:
        marker = " *" if self._has_unsaved_changes else ""
        self.status_var.set(f"{message}{marker}")

    def _show_no_prompt_message(self) -> None:
        messagebox.showinfo(APP_TITLE, "Es ist kein Prompt geladen.")

    def _refresh_session_file_label(self) -> None:
        if self.current_session_file is None:
            self.session_file_var.set("Session: nicht gespeichert")
            return
        self.session_file_var.set(f"Session: {self.current_session_file.name}")

    def _refresh_button_states(self) -> None:
        has_prompts = bool(self.session.prompts)
        current = self.session.current_index
        total = len(self.session.prompts)
        prompt_state = tk.NORMAL if has_prompts else tk.DISABLED
        self.save_session_button.configure(state=prompt_state)
        self.copy_button.configure(state=prompt_state)
        self.paste_button.configure(state=prompt_state)
        self.done_button.configure(state=prompt_state)
        self.skip_button.configure(state=prompt_state)
        self.reset_status_button.configure(state=prompt_state)
        self.save_response_button.configure(state=prompt_state)
        self.previous_button.configure(state=tk.NORMAL if has_prompts and current > 0 else tk.DISABLED)
        self.next_button.configure(state=tk.NORMAL if has_prompts and current < total - 1 else tk.DISABLED)

    def _on_restore_clipboard_changed(self) -> None:
        self.settings.restore_clipboard = bool(self.restore_clipboard_var.get())
        self._save_settings_safely()

    def _on_always_on_top_changed(self) -> None:
        self.settings.always_on_top = bool(self.always_on_top_var.get())
        self.root.attributes("-topmost", self.settings.always_on_top)
        self._save_settings_safely()

    def open_settings_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Prompt-Injector Settings")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#15151b")
        dialog.minsize(520, 520)

        frame = ttk.Frame(dialog, style="Root.TFrame", padding=14)
        frame.pack(fill=tk.BOTH, expand=True)

        restore_var = tk.BooleanVar(value=self.settings.restore_clipboard)
        top_var = tk.BooleanVar(value=self.settings.always_on_top)
        hotkeys_var = tk.BooleanVar(value=self.settings.enable_global_hotkeys)
        auto_send_var = tk.BooleanVar(value=self.settings.auto_send_after_paste)
        target_var = tk.StringVar(value=self.settings.target_window_title)
        hotkey_vars = {
            "copy": tk.StringVar(value=self.settings.hotkeys["copy"]),
            "paste": tk.StringVar(value=self.settings.hotkeys["paste"]),
            "done_next": tk.StringVar(value=self.settings.hotkeys["done_next"]),
            "stop": tk.StringVar(value=self.settings.hotkeys["stop"]),
        }

        ttk.Checkbutton(frame, text="Clipboard nach Einfuegen wiederherstellen", variable=restore_var).pack(anchor=tk.W, pady=(0, 8))
        ttk.Checkbutton(frame, text="Fenster immer im Vordergrund", variable=top_var).pack(anchor=tk.W, pady=(0, 8))
        ttk.Checkbutton(frame, text="Globale Hotkeys aktivieren", variable=hotkeys_var).pack(anchor=tk.W, pady=(0, 12))

        ttk.Label(frame, text="Hotkeys").pack(anchor=tk.W)
        hotkey_grid = ttk.Frame(frame, style="Root.TFrame")
        hotkey_grid.pack(fill=tk.X, pady=(4, 12))
        labels = {
            "copy": "Copy",
            "paste": "Paste",
            "done_next": "Done + Next",
            "stop": "Not-Stopp",
        }
        for row, key in enumerate(("copy", "paste", "done_next", "stop")):
            ttk.Label(hotkey_grid, text=labels[key]).grid(row=row, column=0, sticky="w", pady=2)
            ttk.Entry(hotkey_grid, textvariable=hotkey_vars[key], width=16).grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=2)
        hotkey_grid.grid_columnconfigure(1, weight=1)

        ttk.Label(frame, text="Zielfenster / Anwendung").pack(anchor=tk.W)
        window_row = ttk.Frame(frame, style="Root.TFrame")
        window_row.pack(fill=tk.X, pady=(4, 8))
        target_combo = ttk.Combobox(window_row, textvariable=target_var, values=[], state="normal")
        target_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def refresh_windows() -> None:
            try:
                target_combo.configure(values=list_visible_window_titles())
            except WindowManagerError as exc:
                LOGGER.exception("Fensterliste konnte nicht gelesen werden: %s: %s", type(exc).__name__, exc)
                messagebox.showwarning(APP_TITLE, str(exc), parent=dialog)

        ttk.Button(window_row, text="Aktualisieren", command=refresh_windows).pack(side=tk.LEFT, padx=(8, 0))
        refresh_windows()

        ttk.Checkbutton(frame, text="Automatisch senden nach Einfuegen", variable=auto_send_var).pack(anchor=tk.W, pady=(10, 4))
        ttk.Label(
            frame,
            text="Hinweis: Auto-Send sendet nach Ctrl+V automatisch Enter. Standard ist aus.",
            style="Muted.TLabel",
            wraplength=480,
        ).pack(anchor=tk.W, pady=(0, 14))

        actions = ttk.Frame(frame, style="Root.TFrame")
        actions.pack(fill=tk.X)

        def apply_settings() -> None:
            previous_hotkeys_enabled = self.settings.enable_global_hotkeys
            self.settings.restore_clipboard = bool(restore_var.get())
            self.settings.always_on_top = bool(top_var.get())
            self.settings.enable_global_hotkeys = bool(hotkeys_var.get())
            self.settings.auto_send_after_paste = bool(auto_send_var.get())
            self.settings.target_window_title = target_var.get().strip()
            self.settings.hotkeys = {
                key: hotkey_vars[key].get().strip().lower()
                for key in ("copy", "paste", "done_next", "stop")
            }
            self.settings = InjectorSettings.from_dict(self.settings.to_dict())
            self.root.attributes("-topmost", self.settings.always_on_top)
            self.global_hotkeys_var.set(self.settings.enable_global_hotkeys)

            if previous_hotkeys_enabled or self.hotkeys.is_active:
                self._disable_global_hotkeys(show_errors=True)
            if self.settings.enable_global_hotkeys:
                if not self._enable_global_hotkeys(show_errors=True):
                    self.settings.enable_global_hotkeys = False
                    self.global_hotkeys_var.set(False)

            self._save_settings_safely()
            self._set_status("Settings gespeichert.")
            dialog.destroy()

        ttk.Button(actions, text="Speichern", command=apply_settings).pack(side=tk.RIGHT)
        ttk.Button(actions, text="Abbrechen", command=dialog.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    def _on_global_hotkeys_changed(self) -> None:
        enabled = bool(self.global_hotkeys_var.get())
        if enabled:
            if self._enable_global_hotkeys(show_errors=True):
                self.settings.enable_global_hotkeys = True
            else:
                self.global_hotkeys_var.set(False)
                self.settings.enable_global_hotkeys = False
        else:
            self._disable_global_hotkeys(show_errors=True)
            self.settings.enable_global_hotkeys = False
        self._save_settings_safely()

    def _enable_global_hotkeys(self, show_errors: bool) -> bool:
        callbacks = {
            self.settings.hotkeys["copy"]: lambda: self.root.after(0, self.copy_current_prompt),
            self.settings.hotkeys["paste"]: lambda: self.root.after(0, self.paste_current_prompt),
            self.settings.hotkeys["done_next"]: lambda: self.root.after(0, self.mark_done_and_prepare_next),
            self.settings.hotkeys["stop"]: lambda: self.root.after(0, self.cancel_pending_input),
        }
        try:
            self.hotkeys.register(callbacks)
        except HotkeyError as exc:
            LOGGER.exception("Globale Hotkeys konnten nicht aktiviert werden: %s: %s", type(exc).__name__, exc)
            if show_errors:
                messagebox.showwarning(APP_TITLE, str(exc))
            return False
        self._set_status("Globale Hotkeys aktiv: F6 kopieren, F7 einfuegen, F8 erledigt+weiter, F9 Not-Stopp.")
        LOGGER.info("Globale Hotkeys aktiviert")
        return True

    def _disable_global_hotkeys(self, show_errors: bool) -> None:
        try:
            self.hotkeys.unregister()
        except HotkeyError as exc:
            LOGGER.exception("Globale Hotkeys konnten nicht deaktiviert werden: %s: %s", type(exc).__name__, exc)
            if show_errors:
                messagebox.showwarning(APP_TITLE, str(exc))
            return
        self._set_status("Globale Hotkeys deaktiviert.")
        LOGGER.info("Globale Hotkeys deaktiviert")

    def cancel_pending_input(self) -> None:
        if self._pending_paste_after_id is None:
            self._set_status("Not-Stopp: keine laufende Eingabe geplant.")
            return
        self.root.after_cancel(self._pending_paste_after_id)
        self._pending_paste_after_id = None
        self.root.deiconify()
        self._set_status("Not-Stopp: geplantes Einfuegen abgebrochen.")
        LOGGER.info("Not-Stopp: geplantes Einfuegen abgebrochen")

    def _save_settings_safely(self) -> None:
        self.settings.window_geometry = self.root.geometry()
        try:
            save_settings(self.settings)
        except SettingsError as exc:
            LOGGER.exception("Settings konnten nicht gespeichert werden: %s: %s", type(exc).__name__, exc)
            messagebox.showwarning(APP_TITLE, str(exc))

    def _confirm_unsaved_changes(self) -> bool:
        if not self._has_unsaved_changes:
            return True
        answer = messagebox.askyesnocancel(
            APP_TITLE,
            "Es gibt ungespeicherte Aenderungen.\n\n"
            "Ja: Session jetzt speichern\n"
            "Nein: ohne Speichern fortfahren\n"
            "Abbrechen: Aktion stoppen",
        )
        if answer is None:
            return False
        if answer is True:
            return self.save_session_file()
        return True

    def _on_close(self) -> None:
        if not self._confirm_unsaved_changes():
            return
        self._disable_global_hotkeys(show_errors=False)
        self.cancel_pending_input()
        self.settings.window_geometry = self.root.geometry()
        self._save_settings_safely()
        LOGGER.info("App beendet")
        self.root.destroy()
