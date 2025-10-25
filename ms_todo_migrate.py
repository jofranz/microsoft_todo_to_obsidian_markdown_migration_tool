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
    with open(path, "w", encoding="utf-8") as f:
        # Match shell behaviour: write a JSON representation into a .md file
        json.dump(task_json, f, ensure_ascii=False, indent=2)
    return path


def minimal_task_repr(task: Dict) -> Dict:
    return {
        "title": task.get("title"),
        "importance": task.get("importance"),
        "status": task.get("status"),
        "categories": task.get("categories"),
        "createdDateTime": task.get("createdDateTime"),
        "dueDateTime": task.get("dueDateTime"),
        "body": task.get("body"),
        "completedDateTime": task.get("completedDateTime"),
        "reminderDateTime": task.get("reminderDateTime"),
        "checklistItems": task.get("checklistItems"),
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Migrate MS To Do tasks to files (Python refactor)")
    p.add_argument("--source-token", help="Source account bearer token", required=True)
    p.add_argument("--dest-token", help="Destination account bearer token (not used, optional)", default="")
    p.add_argument("--output-folder", help="Output folder for exported tasks", default="out")
    p.add_argument("--skip-completed", help="Skip completed tasks", action="store_true")
    p.add_argument("--source-base", help="Source lists base URL",
                   default="https://graph.microsoft.com/v1.0/me/todo/lists")
    args = p.parse_args(argv)

    source_token = args.source_token
    output_folder = args.output_folder
    skip_completed = args.skip_completed

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
            path = write_task_file(list_folder, filename_base, payload)
            migrated_count += 1
            print(f"Wrote task '{title}' -> {path}")

        print(f"Migrated {migrated_count} tasks from {display_name}")
        total_migrated += migrated_count

    print(f"Migration completed! Total migrated: {total_migrated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
