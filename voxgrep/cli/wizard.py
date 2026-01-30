"""
State machine for VoxGrep interactive mode.

This module replaces the 126-line interactive_mode() god function with
a clean, testable state machine that handles the interactive wizard flow.
"""

from enum import Enum, auto
from typing import Any, Optional

import questionary

from .config import SessionConfig, SearchConfig, ExportConfig
from .io import CLIContext
from .action_loop import ActionLoop, ActionLoopState, ActionResult, build_search_actions


class WizardPhase(Enum):
    """Phases of the interactive wizard."""

    FILE_SELECTION = auto()
    TASK_SELECTION = auto()
    TRANSCRIPTION_CHECK = auto()
    TASK_EXECUTION = auto()
    SAVE_PREFS = auto()
    CLEANUP = auto()
    EXIT = auto()


class InteractiveWizard:
    """
    State machine implementation of the interactive mode.

    This class manages the flow through the interactive wizard, with each
    phase handled by a dedicated method that returns the next phase.
    """

    def __init__(self, ctx: Optional[CLIContext] = None):
        """
        Initialize the wizard.

        Args:
            ctx: CLI context for dependency injection. If None, uses defaults.
        """
        self.ctx = ctx or CLIContext.default()
        self.session: Optional[SessionConfig] = None
        self.prefs: dict[str, Any] = {}
        self.current_task: Optional[str] = None
        self._reselect_files: bool = False

    def run(self) -> None:
        """Run the interactive wizard until exit."""
        self.ctx.console.print("[bold yellow]Interactive Mode[/bold yellow]")
        self.ctx.console.print("Let's configure your task.\n")

        self.prefs = self.ctx.prefs_loader()

        phase = WizardPhase.FILE_SELECTION

        while phase != WizardPhase.EXIT:
            handler = self._get_phase_handler(phase)
            phase = handler()

    def _get_phase_handler(self, phase: WizardPhase):
        """Get the handler method for a given phase."""
        handlers = {
            WizardPhase.FILE_SELECTION: self._handle_file_selection,
            WizardPhase.TASK_SELECTION: self._handle_task_selection,
            WizardPhase.TRANSCRIPTION_CHECK: self._handle_transcription_check,
            WizardPhase.TASK_EXECUTION: self._handle_task_execution,
            WizardPhase.SAVE_PREFS: self._handle_save_prefs,
            WizardPhase.CLEANUP: self._handle_cleanup,
        }
        return handlers.get(phase, lambda: WizardPhase.EXIT)

    def _handle_file_selection(self) -> WizardPhase:
        """Handle file selection phase."""
        from .workflows import select_input_files

        input_files = select_input_files(self.ctx)
        if not input_files:
            return WizardPhase.EXIT

        self.ctx.console.print(f"[green]Selected {len(input_files)} files.[/green]\n")

        # Create session config from preferences
        self.session = SessionConfig.from_prefs(self.prefs, input_files)

        return WizardPhase.TASK_SELECTION

    def _handle_task_selection(self) -> WizardPhase:
        """Handle main task selection."""
        if self.session is None:
            return WizardPhase.FILE_SELECTION

        task = self.ctx.prompts.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("Search", value="search"),
                questionary.Choice("Transcription Only", value="transcribe"),
                questionary.Choice("Calculate N-grams", value="ngrams"),
                questionary.Separator(),
                questionary.Choice("Manage Selected Files (Rename, Remove...)", value="manage_files"),
                questionary.Choice("Settings (Ignored Words, etc.)", value="settings_menu"),
                questionary.Choice("Change/Reselect Files", value="change_files"),
                questionary.Choice("Exit", value="exit"),
            ],
            default="search",
        )

        if task is None or task == "exit":
            return WizardPhase.EXIT

        if task == "change_files":
            return WizardPhase.FILE_SELECTION

        if task == "manage_files":
            return self._handle_manage_files()

        if task == "settings_menu":
            return self._handle_settings_menu()

        self.current_task = task
        return WizardPhase.TRANSCRIPTION_CHECK

    def _handle_manage_files(self) -> WizardPhase:
        """Handle file management submenu."""
        from .workflows import manage_files_menu

        if self.session is None:
            return WizardPhase.FILE_SELECTION

        # Note: manage_files_menu doesn't support ctx yet - uses questionary directly
        self.session.input_files = manage_files_menu(self.session.input_files)

        if not self.session.input_files:
            self.ctx.console.print("[yellow]All files removed. Please select files again.[/yellow]")
            return WizardPhase.FILE_SELECTION

        return WizardPhase.TASK_SELECTION

    def _handle_settings_menu(self) -> WizardPhase:
        """Handle global settings menu."""
        from .workflows import settings_menu

        if self.session is None:
            return WizardPhase.FILE_SELECTION

        ignored_words, use_ignored_words = settings_menu(self.prefs, self.ctx)
        self.session.search.ignored_words = ignored_words
        self.session.search.use_ignored_words = use_ignored_words

        return WizardPhase.TASK_SELECTION

    def _handle_transcription_check(self) -> WizardPhase:
        """Check if transcription is needed and configure if so."""
        from .workflows import check_transcripts, configure_transcription

        if self.session is None:
            return WizardPhase.FILE_SELECTION

        if self.current_task == "transcribe":
            self.session.transcribe = True
            args = self.session.to_namespace()
            configure_transcription(args, self.prefs, self.ctx)
            self.session = SessionConfig.from_namespace(args)
            return WizardPhase.TASK_EXECUTION

        if self.current_task == "ngrams":
            should_transcribe, missing_files = check_transcripts(self.session.input_files, self.ctx)
            if should_transcribe:
                self.session.transcribe = True
                args = self.session.to_namespace()
                configure_transcription(args, self.prefs, self.ctx)
                self.session = SessionConfig.from_namespace(args)
            elif missing_files:
                self.ctx.console.print("[bold red]Error: Cannot calculate n-grams without transcripts.[/bold red]")
                return WizardPhase.TASK_SELECTION
            return WizardPhase.TASK_EXECUTION

        # search task
        should_transcribe, _ = check_transcripts(self.session.input_files, self.ctx)
        if should_transcribe:
            self.session.transcribe = True
            args = self.session.to_namespace()
            configure_transcription(args, self.prefs, self.ctx)
            self.session = SessionConfig.from_namespace(args)

        return WizardPhase.TASK_EXECUTION

    def _handle_task_execution(self) -> WizardPhase:
        """Execute the selected task."""
        from .commands import run_transcription_whisper
        from .ngrams import interactive_ngrams_workflow

        if self.session is None:
            return WizardPhase.FILE_SELECTION

        try:
            # Run transcription first if needed
            if self.session.transcribe:
                run_transcription_whisper(
                    self.session.input_files,
                    self.session.transcription.model,
                    self.session.transcription.device,
                    self.session.transcription.compute_type,
                    self.session.transcription.language,
                    self.session.transcription.prompt,
                    self.session.transcription.beam_size,
                    self.session.transcription.best_of,
                    self.session.transcription.vad_filter,
                    self.session.transcription.normalize_audio,
                    translate=self.session.transcription.translate,
                )
                self.ctx.console.print("[green]Transcription complete[/green]\n")
                self.session.transcribe = False

            # Execute the specific task
            if self.current_task == "search":
                if not self._execute_search_workflow():
                    return WizardPhase.EXIT
            elif self.current_task == "ngrams":
                if not self._execute_ngrams_workflow():
                    return WizardPhase.TASK_SELECTION
            else:
                # transcribe only - already done above
                self.ctx.console.print("\n[dim]--- Task Complete ---[/dim]\n")

        except KeyboardInterrupt:
            self.ctx.console.print("\n[dim]Returning to menu...[/dim]\n")
            return WizardPhase.TASK_SELECTION
        except Exception as e:
            self.ctx.console.print(f"\n[bold red]Error:[/bold red] {e}\n")
            self.ctx.console.print("[dim]Returning to menu...[/dim]\n")
            return WizardPhase.TASK_SELECTION

        return WizardPhase.SAVE_PREFS

    def _execute_search_workflow(self) -> bool:
        """
        Execute the search workflow with action loop.

        Returns:
            True to continue to task selection, False to exit
        """
        if self.session is None:
            return True

        # Get search terms
        search_input = self.ctx.prompts.text("Enter search terms (comma separated):")
        if not search_input:
            return True

        self.session.search.query = [s.strip() for s in search_input.split(',') if s.strip()]

        # Select search type
        search_type = self.ctx.prompts.select(
            "Search Type",
            choices=["sentence", "fragment", "mash", "semantic"],
            default=self.session.search.search_type,
        )
        if search_type:
            self.session.search.search_type = search_type

        # Run search action loop
        return self._run_search_action_loop()

    def _run_search_action_loop(self) -> bool:
        """
        Run the search action loop.

        Returns:
            True to continue, False to exit
        """
        if self.session is None:
            return True

        from .workflows import get_output_filename, post_export_menu
        from .commands import run_voxgrep_search
        from .ui import print_session_summary

        def get_default_output_name() -> str:
            """Get a safe default output name from search terms."""
            default_out = "supercut"
            if self.session and self.session.search.query:
                safe_term = "".join([
                    c if c.isalnum() or c in (' ', '-', '_') else ''
                    for c in self.session.search.query[0]
                ]).strip().replace(' ', '_')
                if safe_term:
                    default_out = safe_term
            return default_out

        while True:
            default_out = get_default_output_name()
            padding_display = self.session.search.padding or 0
            max_display = self.session.search.maxclips or "All"

            action = self.ctx.prompts.select(
                "Next Step:",
                choices=[
                    questionary.Choice("Preview Results (MPV)", value="preview"),
                    questionary.Choice(f"Export Supercut (to {default_out}.mp4...)", value="export"),
                    questionary.Separator(),
                    questionary.Choice(
                        f"Settings (Padding: {padding_display}s, Max: {max_display})",
                        value="settings"
                    ),
                    questionary.Choice("Start Over (New Search)", value="cancel"),
                ],
                default="preview",
            )

            if action == "cancel":
                return True

            if action == "preview":
                self.ctx.console.print("\n[bold yellow]Generating Preview...[/bold yellow]")
                result = run_voxgrep_search(
                    files=self.session.input_files,
                    query=self.session.search.query,
                    search_type=self.session.search.search_type,
                    output=self.session.export.output,
                    maxclips=self.session.search.maxclips,
                    padding=self.session.search.padding,
                    demo=False,
                    random_order=self.session.search.randomize,
                    resync=self.session.search.resync,
                    export_clips=self.session.export.export_clips,
                    write_vtt=self.session.export.write_vtt,
                    preview=True,
                    exact_match=self.session.search.exact_match,
                    burn_in_subtitles=self.session.export.burn_in_subtitles,
                )
                if isinstance(result, dict):
                    print_session_summary(result)
                continue

            if action == "settings":
                self._configure_search_settings()
                continue

            if action == "export":
                self.session.export.preview = False
                self.session.export.demo = False
                self.session.export.output = get_output_filename(
                    self.session.search.query,
                    default_out,
                    self.ctx
                )

                result = run_voxgrep_search(
                    files=self.session.input_files,
                    query=self.session.search.query,
                    search_type=self.session.search.search_type,
                    output=self.session.export.output,
                    maxclips=self.session.search.maxclips,
                    padding=self.session.search.padding,
                    demo=False,
                    random_order=self.session.search.randomize,
                    resync=self.session.search.resync,
                    export_clips=self.session.export.export_clips,
                    write_vtt=self.session.export.write_vtt,
                    preview=False,
                    exact_match=self.session.search.exact_match,
                    burn_in_subtitles=self.session.export.burn_in_subtitles,
                )

                if isinstance(result, dict) and result.get("success"):
                    print_session_summary(result)

                if result:
                    while True:
                        post_action = post_export_menu(self.session.export.output)
                        if post_action == "edit":
                            break
                        elif post_action in ("new", "menu"):
                            return True

                    if post_action == "edit":
                        continue

                return True

        return True

    def _configure_search_settings(self) -> None:
        """Configure search-specific settings interactively."""
        from .workflows import search_settings_menu

        if self.session is None:
            return

        args = self.session.to_namespace()
        search_settings_menu(args, self.ctx)
        self.session = SessionConfig.from_namespace(args)

    def _execute_ngrams_workflow(self) -> bool:
        """
        Execute the n-grams workflow.

        Returns:
            True if completed normally, False if should return to task selection
        """
        from .workflows import check_transcripts
        from .ngrams import interactive_ngrams_workflow

        if self.session is None:
            return False

        # Double-check transcripts
        _, missing_files = check_transcripts(self.session.input_files, self.ctx)
        if missing_files:
            self.ctx.console.print("[red]Cannot proceed with n-grams: Transcripts missing.[/red]")
            return False

        # Get N value
        n_str = self.ctx.prompts.text("Enter N for N-grams", default="1")
        self.session.ngrams = int(n_str) if n_str else 1

        # Run the interactive workflow
        args = self.session.to_namespace()
        interactive_ngrams_workflow(args, self.ctx)

        self.ctx.console.print("\n[dim]--- Task Complete ---[/dim]\n")
        return True

    def _handle_save_prefs(self) -> WizardPhase:
        """Save preferences after task completion."""
        if self.session is not None:
            prefs_update = self.session.to_prefs_update()
            self.prefs.update(prefs_update)
            self.ctx.prefs_saver(self.prefs)

        return WizardPhase.TASK_SELECTION

    def _handle_cleanup(self) -> WizardPhase:
        """Cleanup phase before exit."""
        return WizardPhase.EXIT


def interactive_mode(ctx: Optional[CLIContext] = None) -> None:
    """
    Run the interactive wizard.

    This is the main entry point that replaces the original interactive_mode().

    Args:
        ctx: Optional CLI context for dependency injection
    """
    wizard = InteractiveWizard(ctx)
    wizard.run()
