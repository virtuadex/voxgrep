# Interactive Mode Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Start Interactive Mode                    │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Select Input Files     │
                    └────────────┬────────────┘
                                 │
                                 ▼
        ┌────────────────────────────────────────────┐
        │          MAIN MENU LOOP (while True)       │
        │                                            │
        │  ? What would you like to do?              │
        │    ❯ Search                                │
        │      Transcription Only                    │
        │      Calculate N-grams                     │
        │      ────────────────                      │
        │      Settings                              │
        │      Change Files                          │
        │      Exit                                  │
        └────────────┬───────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │   User Selects Task            │
        └────────┬───────────────────────┘
                 │
                 ├─────────────┬─────────────┬──────────────┐
                 │             │             │              │
                 ▼             ▼             ▼              ▼
         ┌───────────┐  ┌──────────┐  ┌─────────┐   ┌──────────┐
         │  Search   │  │Transcribe│  │ N-grams │   │  Exit    │
         └─────┬─────┘  └────┬─────┘  └────┬────┘   └────┬─────┘
               │             │             │              │
               │             │             │              ▼
               │             │             │         [Exit App]
               │             │             │
               │             ▼             │
               │    ┌────────────────┐    │
               │    │  TRY BLOCK     │    │
               │    │  Execute Task  │    │
               │    └───┬────────┬───┘    │
               │        │        │        │
               │        │        │        │
               │    Success   Error/     │
               │        │     Cancel     │
               │        │        │        │
               │        ▼        ▼        │
               │    ┌────────────────┐   │
               │    │ Task Complete  │   │
               │    └───────┬────────┘   │
               │            │            │
               │            │            │
               │    ┌───────▼────────┐   │
               │    │ Save Prefs     │   │
               │    └───────┬────────┘   │
               │            │            │
               └────────────┴────────────┘
                            │
                            │
                            ▼
                    ┌───────────────┐
                    │   CONTINUE    │
                    │  (Loop Back)  │
                    └───────┬───────┘
                            │
                            │
                            └──────────┐
                                       │
                                       ▼
                    ┌──────────────────────────────┐
                    │  Back to Main Menu           │
                    │  (User can do another task)  │
                    └──────────────────────────────┘
```

## Key Points

1. **Infinite Loop**: The main menu is in a `while True` loop
2. **Try-Except**: Task execution is wrapped to catch errors
3. **Continue**: Both success and errors use `continue` to loop back
4. **Exit**: Only explicit "Exit" choice breaks the loop
5. **Preferences**: Saved after each successful task

## Exception Handling

```python
try:
    execute_task()
    print("Task Complete")
except KeyboardInterrupt:
    print("Returning to menu...")
    continue  # ← Goes back to menu
except Exception as e:
    print(f"Error: {e}")
    continue  # ← Goes back to menu
```

## User Journey Example

```
1. User: [Starts voxgrep]
   → Shows main menu

2. User: [Selects "Transcription Only"]
   → Transcribes video
   → "Task Complete"
   → Shows main menu again ✓

3. User: [Selects "Search"]
   → Performs search
   → Shows results
   → Shows main menu again ✓

4. User: [Selects "Exit"]
   → Application exits
```
