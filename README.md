# MS To Do migration (shell -> Python)

## Motivation
Microsoft To Do's data export (takeout) process appears to be broken. I started by porting https://github.com/Shadoxity/Scripts into a shell script, and then refactored that into this Python script to make it more robust and easier to use.

## Install

This repository contains a Python refactor of `MS-Todo-Migrate-to-another-account.sh`.

Important files:

- `ms_todo_migrate.py` — Python script that fetches lists and tasks from Microsoft Graph and writes each task to a `.md` file under an output folder.
- `requirements.txt` — lists `requests` and `PyYAML` for YAML frontmatter support.

## Quick start

There are two common ways to run the script. The recommended approach for CLI tools is to use pipx; if you prefer a simple local setup, use a virtual environment.

Option A — pipx (recommended for installed CLI tools)

1. Install pipx (if you don't have it):

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

2. If you package this project (add a `pyproject.toml` or `setup.py` and a console entry point), you can install it into an isolated environment managed by pipx:

```bash
# from the project root (after making the project installable)
pipx install .
# then run the installed CLI (if you added a console script)
ms-todo-migrate --source-token "<SOURCE_TOKEN>" --skip-completed
```

Option B — local virtual environment (simple, works now)

1. Create and activate a virtualenv, then install requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

2. Run the script (provide a source bearer token):

```bash
python3 ms_todo_migrate.py --source-token "<SOURCE_TOKEN>" --output-folder out --skip-completed
```

Notes

- The script only reads from the source account. Destination operations from the original shell script were commented out; this refactor preserves that behavior and writes tasks to local files.
- Tasks are exported as Markdown files with YAML frontmatter (Obsidian properties).
- Each task includes:
  - YAML frontmatter with task properties
  - Subtasks table (if any checklist items exist)
  - Task body content (if any) or JSON representation
- Filenames are sanitized:
  - Each "?" is replaced with "_" (preserving position)
  - Special characters and spaces become underscores
  - Dots in filenames are preserved

## Features (implemented and open)
Completed features:
- [x] Transform tasks to Obsidian-compatible markdown with YAML frontmatter
- [x] Render checklist items as a "Subtasks" table
- [x] Replace each "?" with "_" in filenames
- [x] Convert importance "high" to boolean property "is_starred"
- [x] Token validation with helpful error messages

Not implemented features:
- [ ] Implement nested folders for task organization
- [ ] Add optional prefix property to all notes to indicate MsToDo source
- [ ] Support for destination account operations (task creation via Graph API)
- [ ] Add task categorization support
