#!/usr/bin/env python3
"""MS To Do migration helper (shell -> Python refactor)

This script mirrors the behaviour of the original
`MS-Todo-Migrate-to-another-account.sh`:
- fetch lists from a source account
- fetch tasks for each list (handles paging)
- optionally skip completed tasks
- write each task to a file under an output folder (one file per task)

Usage: see README.md or run with -h
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, Iterable, List, Optional

import requests
import yaml


def fetch_all(url: str, token: str) -> List[Dict]:
    """Fetch all pages of a Microsoft Graph collection starting at `url`.

    Returns the concatenated list of items (the `.value` arrays).
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    items: List[Dict] = []
    next_link: Optional[str] = url
    while next_link:
        resp = requests.get(next_link, headers=headers)
        resp.raise_for_status()
        body = resp.json()
        value = body.get("value", [])
        if isinstance(value, list):
            items.extend(value)
        # nextLink may be absent or None
        next_link = body.get("@odata.nextLink")
    return items


def validate_token(token: str) -> tuple[bool, Optional[str]]:
    """Quickly validate a Microsoft Graph bearer token by calling /me.

    Returns (True, None) on success. On failure returns (False, message) where message
    gives a short diagnostic (status code and reason).
    """
    if not token:
        return False, "no token provided"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, timeout=10)
    except requests.RequestException as e:
        return False, f"request error: {e}"
    if resp.status_code == 200:
        return True, None
    # Provide helpful diagnostics for common cases (401/403)
    if resp.status_code == 401:
        return False, "401 Unauthorized: token may be expired or invalid"
    if resp.status_code == 403:
        return False, "403 Forbidden: token may be missing required scopes"
    return False, f"{resp.status_code} {resp.reason}"


def safe_filename(title: str) -> str:
    # Replace slashes, colons and whitespace with underscores; keep it short
    s = re.sub(r"[:/\\\s]+", "_", title)
    s = s.strip("_\n\r")
    if not s:
        s = "untitled"
    # Ensure filename is not too long
    return s[:150]


def write_task_file(folder: str, filename_base: str, task_json: Dict) -> str:
    os.makedirs(folder, exist_ok=True)
    filename = f"{filename_base}.md"
    path = os.path.join(folder, filename)
    # Avoid overwriting if duplicate title exists: append a counter
    counter = 1
    base = filename_base
    while os.path.exists(path):
        filename = f"{base}_{counter}.md"
        path = os.path.join(folder, filename)
        counter += 1
    # original_task is optional; if provided, we'll render checklist items below the note
    with open(path, "w", encoding="utf-8") as f:
        # Write Obsidian-compatible YAML frontmatter (properties)
        # Use PyYAML to emit a readable YAML block; keep keys order for readability
        # Exclude any internal checklist items from the frontmatter properties
        frontmatter_data = None
        try:
            frontmatter_data = dict(task_json) if isinstance(task_json, dict) else task_json
            if isinstance(frontmatter_data, dict):
                frontmatter_data.pop("_checklistItems", None)
            yaml_str = yaml.safe_dump(frontmatter_data, allow_unicode=True, sort_keys=False)
        except Exception:
            # Fallback: use a JSON dump inside the frontmatter if YAML serialization fails
            # Ensure checklist items are excluded from the fallback as well
            fm = dict(task_json) if isinstance(task_json, dict) else task_json
            if isinstance(fm, dict):
                fm.pop("_checklistItems", None)
            yaml_str = json.dumps(fm, ensure_ascii=False, indent=2)

        f.write("---\n")
        f.write(yaml_str)
        f.write("---\n\n")

        # Render checklist items (if any) as a Markdown table under a "## Subtasks" heading.
        # Only use `isChecked` and `displayName` fields.
        original_items = None
        # The caller may embed original checklist items into a special key; check for that first
        if isinstance(task_json, dict):
            original_items = task_json.get("_checklistItems")
        # If not present, see if the calling code passed a separate list via a local variable
        if not original_items:
            # No checklist items to render
            original_items = None

        if original_items and isinstance(original_items, list) and len(original_items) > 0:
            def esc(s: str) -> str:
                return (s or "").replace("|", "\\|")

            f.write("\n## Subtasks\n\n")
            f.write("| Status | Item |\n")
            f.write("| --- | --- |\n")
            for it in original_items:
                checked = it.get("isChecked")
                # Convert boolean to "done" or "to do"
                checked_str = "done" if checked else "to do"
                display = esc(it.get("displayName") or "")
                f.write(f"| {checked_str} | {display} |\n")
            f.write("\n")  # Add blank line after table

        # If the task has a body content (common in MS To Do), append it as the note
        body = None
        if isinstance(task_json, dict):
            b = task_json.get("body")
            if isinstance(b, dict):
                body = b.get("content")

        if body:
            # Write the body content as markdown
            f.write(str(body))
            if not str(body).endswith("\n"):
                f.write("\n")
        else:
            # Otherwise include the full JSON for reference in a fenced code block
            f.write("```json\n")
            json.dump(task_json, f, ensure_ascii=False, indent=2)
            f.write("\n```\n")
    return path


def minimal_task_repr(task: Dict) -> Dict:
    importance = (task.get("importance") or "").lower()
    return {
        "title": task.get("title"),
        # "importance": task.get("importance"), Removed as it got migrated in "is_starred"
        "is_starred": True if importance == "high" else False,
        # "status": task.get("status"), Do NOT include status as it always returns "notStarted"
        # "categories": task.get("categories"), Do NOT include status as it's array is always empty
        "createdDateTime": task.get("createdDateTime"),
        "dueDateTime": task.get("dueDateTime"),
        "body": task.get("body"),
        "completedDateTime": task.get("completedDateTime"),
        "reminderDateTime": task.get("reminderDateTime"),
        # Do NOT include checklistItems here; they will be rendered in the markdown body
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Migrate MS To Do tasks to files (Python refactor)")
    p.add_argument("--source-token", help="Source account bearer token", required=True)
    p.add_argument("--dest-token", help="Destination account bearer token (not used, optional)", default="")
    p.add_argument("--output-folder", help="Output folder for exported tasks", default="out")
    p.add_argument("--skip-completed", help="Skip completed tasks", action="store_true")
    p.add_argument("--source-base", help="Source lists base URL",
                   default="https://graph.microsoft.com/v1.0/me/todo/lists")
    p.add_argument("--validate-token", help="Validate source token and exit (no migration)", action="store_true")
    args = p.parse_args(argv)

    source_token = args.source_token
    output_folder = args.output_folder
    skip_completed = args.skip_completed

    # If requested, validate token and exit with status 0 on success, non-zero on failure.
    if args.validate_token:
        ok, msg = validate_token(source_token)
        if ok:
            print("Token appears valid.")
            return 0
        else:
            print("Token validation failed:", msg, file=sys.stderr)
            return 3

    # Early validation to give a clearer error message if token is invalid/expired.
    ok, msg = validate_token(source_token)
    if not ok:
        print("Failed to validate source token:", msg, file=sys.stderr)
        print("If your token is a short-lived OAuth token it may have expired. Obtain a new bearer token and retry.")
        return 3

    print("Fetching source lists...")
    try:
        source_lists = fetch_all(args.source_base, source_token)
    except requests.HTTPError as e:
        print("Failed to fetch source lists:", e, file=sys.stderr)
        return 2

    total_migrated = 0
    for source in source_lists:
        display_name = source.get("displayName", "untitled_list")
        list_id = source.get("id")
        wellknown = source.get("wellknownListName")
        print(f"Processing list: {display_name} (id={list_id}) wellknown={wellknown}")

        cleaned = re.sub(r"[\s/]+", "", display_name)
        list_folder = os.path.join(output_folder, cleaned)

        # fetch tasks for the list
        tasks_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks"
        try:
            tasks = fetch_all(tasks_url, source_token)
        except requests.HTTPError as e:
            print(f"Failed to fetch tasks for {display_name}: {e}", file=sys.stderr)
            continue

        print(f"Found {len(tasks)} tasks in {display_name}")
        migrated_count = 0
        for task in tasks:
            status = task.get("status")
            title = task.get("title") or "untitled"
            if skip_completed and status == "completed":
                continue
            filename_base = safe_filename(title)
            payload = minimal_task_repr(task)
            # Attach checklist items under an internal key so they are NOT included in frontmatter
            payload["_checklistItems"] = task.get("checklistItems")
            path = write_task_file(list_folder, filename_base, payload)
            migrated_count += 1
            print(f"Wrote task '{title}' -> {path}")

        print(f"Migrated {migrated_count} tasks from {display_name}")
        total_migrated += migrated_count

    print(f"Migration completed! Total migrated: {total_migrated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
