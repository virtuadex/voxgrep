---
name: Code Maintenance & Sync
description: Comprehensive guide for troubleshooting code, identifying improvements, and ensuring documentation remains synchronized with code changes.
---

# Code Maintenance & Sync Skill

This skill outlines the standard operating procedure for maintaining the VoxGrep codebase. It focuses on three pillars: **Troubleshooting**, **Improvement**, and **Documentation Synchronization**.

## 1. 🔍 Troubleshooting Protocol

When addressing bugs or installation issues:

1.  **Run Diagnostics First**:
    *   Always utilize the built-in doctor tool (`poetry run voxgrep --doctor`) to gather environmental context.
    *   Check specifically for platform-specific constraints (e.g., Python 3.13 on Windows, Apple Silicon vs Intel).

2.  **Isolate the Component**:
    *   Determine if the issue is in the **Core (Python)**, **Dependencies (Poetry/System)**, or **Platform (Win/Mac/Linux)**.
    *   Test isolated reproduction scripts before modifying the main codebase.

3.  **Verify Fixes**:
    *   After applying a fix, rerun the diagnosis.
    *   If the fix involves a new dependency, verify it works on a clean environment if possible.

## 2. ⚡ Code Improvement Strategy

When reviewing or writing code, look for:

1.  **Platform Abstraction**:
    *   avoid hardcoded paths (use `pathlib`).
    *   Wrap system calls (like `ffmpeg`, `mpv`) in checks that provide helpful error messages if missing.

2.  **User Experience (UX) First**:
    *   Installation should be one-click where possible (see `installvoxgrep.ps1`).
    *   Error messages should suggest solutions, not just stack traces.

3.  **Performance**:
    *   Check for redundant checks (e.g., checking for a binary every time vs checking once).
    *   Optimize imports to reduce startup time.

## 3. 📚 Documentation Synchronization (CRITICAL)

**Rule:** *No code change is complete until the documentation reflects it.*

Whenever you modify code, checking the documentation is **mandatory**.

### Check List:

| If you changed... | You MUST update... |
| :--- | :--- |
| **CLI Flags / Arguments** | `docs/CLI_REFERENCE.md` and `voxgrep --help` output checks. |
| **Installation Steps** | `docs/GETTING_STARTED.md`, `README.md`, and `installvoxgrep.ps1`. |
| **New Features** | `README.md` (Features list) and `docs/USER_GUIDE.md`. |
| **Dependencies** | `pyproject.toml` and verify `docs/GETTING_STARTED.md` prerequisites. |

### Sync Process:

1.  **Identify Impact**: Does this code change how the user *installs*, *runs*, or *configures* the app?
2.  **Search Docs**: grep for keywords related to your change in `docs/` to find outdated references.
3.  **Update**: rewriting the relevant sections to match the new reality.
4.  **Verify**: Read the new doc section as if you were a new user. Does it work?

## 4. 🛠️ Common Maintenance Tasks

### Updating the Installer
If `pyproject.toml` changes significantly (e.g., dropping Python 3.10 support), you **MUST** update the version checks in `installvoxgrep.ps1`.

### Doctor Check
If a new system dependency (like `mpv`) is added, update `voxgrep/doctor.py` to check for it so users get immediate feedback.
