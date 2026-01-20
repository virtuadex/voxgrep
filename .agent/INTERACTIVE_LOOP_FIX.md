# Interactive Mode Loop Fix

## Issue
After completing a transcription task in interactive mode, the application would exit instead of returning to the main menu.

## Root Cause
The `interactive_mode()` function in `voxgrep/cli/interactive.py` did not have proper exception handling around task execution. When `KeyboardInterrupt` or other exceptions were raised during transcription, they would propagate up and exit the loop.

## Solution
Wrapped the task execution block in a `try-except` block to catch:
1. **KeyboardInterrupt**: When user cancels with Ctrl+C
2. **General Exceptions**: Any other errors during task execution

Both cases now:
- Display an appropriate message
- Use `continue` to return to the menu
- Preserve the main loop

## Changes Made

### File: `voxgrep/cli/interactive.py`

```python
# Handle specific tasks
try:
    if task == "search":
        if not handle_search_workflow(args):
            break
    elif task == "ngrams":
        args.ngrams = int(questionary.text("Enter N for N-grams", default="1").ask())
        interactive_ngrams_workflow(args)
        console.print("\n[dim]--- Task Complete ---[/dim]\n")
    else:
        # Transcription only
        execute_args(args)
        console.print("\n[dim]--- Task Complete ---[/dim]\n")
except KeyboardInterrupt:
    # User cancelled - just continue to menu
    console.print("\n[dim]Returning to menu...[/dim]\n")
    continue
except Exception as e:
    console.print(f"\n[bold red]Error:[/bold red] {e}\n")
    console.print("[dim]Returning to menu...[/dim]\n")
    continue
```

## User Experience

### Before
```
? What would you like to do? Transcription Only
[Transcription completes]
--- Task Complete ---
[Application exits]
```

### After
```
? What would you like to do? Transcription Only
[Transcription completes]
--- Task Complete ---

? What would you like to do?
  ❯ Search
    Transcription Only
    Calculate N-grams
    ────────────────
    Settings (Ignored Words, etc.)
    Change Files
    Exit
```

## Benefits

1. **Better UX**: Users can perform multiple tasks without restarting
2. **Error Recovery**: Errors don't crash the entire session
3. **Workflow Efficiency**: Transcribe → Search → Export in one session
4. **Graceful Cancellation**: Ctrl+C returns to menu instead of exiting

## Example Workflow

Now users can:
1. Select video files
2. Transcribe with one model
3. See it's not good quality
4. Transcribe again with better model (prompted about existing)
5. Search the transcript
6. Export supercut
7. Search again with different query
8. All without leaving interactive mode!
