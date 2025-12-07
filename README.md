# Microsoft ToDo to Obsidian markdown migration tool


## Motivation
Microsoft To Do's data export (takeout) process appears to be broken. I started by porting https://github.com/Shadoxity/Scripts into a shell script, and then refactored that into this Python script to make it more robust and easier to use.

## Install

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
ms-todo-migrate --source-token "<MICROSOFT_API_TOKEN>" --skip-completed
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
python3 ms_todo_migrate.py --source-token "<MICROSOFT_API_TOKEN>" --output-folder folder_name
```

   Additional options:
   - `--skip-completed` — Skip completed tasks entirely (do not write them)
   - `--validate-token` — Validate token and exit without migrating
   - `--output-folder <path>` — Output directory (default: `out`)

## Auth
You need the MICROSOFT_API_TOKEN to access the Microsoft API:
- Visit: https://developer.microsoft.com/en-us/graph/graph-explorer
- Login with your Microsoft account which ToDo is bound to
- Select "Access Token" tab
- Copy access token

## Output Format

Each task is exported as a Markdown file with:

1. **YAML Frontmatter (Properties)** — Obsidian-compatible properties including:
   - `title` — Task title (newlines replaced with spaces)
   - `created` — Task creation date (YYYY-MM-DD format only)
   - `due` — Due date (YYYY-MM-DD format only)
   - `is_starred` — Boolean flag (true if importance is "high")
   - Empty/null fields are excluded (e.g., no `completedDateTime` if not set)

2. **Subtasks Section** — If the task has checklist items:
   - Heading: `## Subtasks`
   - Format: Checkbox list (`- [x]` or `- [ ]`)
   - Displays item name and checked status

3. **Horizontal Rule** — Separator between metadata and content (`---`)

4. **Task Content** — Body text if present, or marker `#ms_todo_no_imported_text` if empty

## Filename Handling

- Question marks (`?`) are individually replaced with underscores (`_`)
- Double quotes (`\"`) are replaced with underscores (`_`)
- Spaces and special characters (`:`, `/`, `\`) become underscores
- Dots (`.`) in filenames are preserved
- If a file already exists:
  - First attempt: append `_from_ms_todo`
  - If that exists: append `_from_ms_todo_2`, `_from_ms_todo_3`, etc.

## Completed Tasks

- When `--skip-completed` is set: completed tasks are skipped entirely
- When `--skip-completed` is NOT set: completed tasks are written to a `deleted/` subfolder within each list folder

## Notes

- The script only reads from the source account. Destination operations from the original shell script were removed.
- Tasks are exported as Markdown files with YAML frontmatter (Obsidian properties).

## Validation and debugging

- Use `--validate-token` to test your Microsoft Graph API token before running a full migration: `python3 ms_todo_migrate.py --validate-token --source-token INSERT_TOKEN_HERE`
- Default placeholder for missing titles: `"untitled"`, `no title`, `no item content`
- Check console output for error messages during migration

## Implemented Features

- [x] Transform tasks to Obsidian-compatible markdown with YAML frontmatter (properties)
- [x] Render subtask checklist items with status (done/to do)
- [x] Replace each `?` with `_` in filenames (position-preserving)
- [x] Convert importance "high" to `is_starred: true` property
- [x] Token validation with helpful error messages
- [x] Filename collision handling with postfix (`_from_ms_todo`, `_from_ms_todo_2`, etc.)
- [x] Completed tasks in separate `deleted/` subfolder (when not using `--skip-completed`)
- [x] Remove empty `completedDateTime` and `reminderDateTime` from properties
- [x] Strip newlines from task titles and subtask names
- [x] Extract and format dates (YYYY-MM-DD only, no timestamps)
- [x] Handle Microsoft Graph datetime objects with timezone info

## Planned Features

- [ ] Implement nested folder organization for task hierarchies
- [ ] Add optional source marker property to notes to mark imported files
- [ ] Add task categorization/tagging support
- [ ] Verify date handling for `.0000000` timestamps during daylight saving time changes
