from __future__ import annotations

import os
from pathlib import Path
import shutil

from .planner import PlannedFile


def resolve_target_path(target_path: Path) -> Path:
    if not target_path.exists():
        return target_path
    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent
    for index in range(1, 1000):
        candidate = parent / f"{stem}__{index}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Unable to resolve unique filename for {target_path}")


def organize_files(rows: list[PlannedFile], apply_changes: bool) -> dict[str, int]:
    summary = {"moved": 0, "skipped": 0}
    to_move = [row for row in rows if row.action in {"keep", "duplicate"}]

    for row in to_move:
        if not apply_changes:
            summary["skipped"] += 1
            continue
        target_path = resolve_target_path(row.target_path)
        if row.file_path.resolve() == target_path.resolve():
            summary["skipped"] += 1
            continue
        os.makedirs(target_path.parent, exist_ok=True)
        shutil.move(str(row.file_path), str(target_path))
        summary["moved"] += 1
    return summary


def delete_duplicates(rows: list[PlannedFile], apply_changes: bool) -> dict[str, int]:
    summary = {"deleted": 0, "skipped": 0}
    duplicates = [row for row in rows if not row.is_original]

    for row in duplicates:
        if not apply_changes:
            summary["skipped"] += 1
            continue
        if row.file_path.resolve() == row.original_path.resolve():
            summary["skipped"] += 1
            continue
        try:
            row.file_path.unlink()
            summary["deleted"] += 1
        except OSError:
            summary["skipped"] += 1
    return summary


def delete_empty_folders(root: Path, apply_changes: bool) -> dict[str, int]:
    summary = {"deleted": 0, "skipped": 0}
    if not root.exists():
        return summary
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        path = Path(dirpath)
        if path == root:
            continue
        if path.name.startswith("."):
            summary["skipped"] += 1
            continue
        if any(name for name in dirnames if not name.startswith(".")):
            summary["skipped"] += 1
            continue
        if filenames:
            summary["skipped"] += 1
            continue
        if not apply_changes:
            summary["skipped"] += 1
            continue
        try:
            path.rmdir()
            summary["deleted"] += 1
        except OSError:
            summary["skipped"] += 1
    return summary
