from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess

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


def _format_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value).strftime("%Y:%m:%d %H:%M:%S")


def _preserve_timestamps(target_path: Path, btime: float, mtime: float) -> None:
    if not target_path.exists():
        return
    if btime <= 0 and mtime <= 0:
        return
    create_time = _format_timestamp(btime if btime > 0 else mtime)
    modify_time = _format_timestamp(mtime if mtime > 0 else btime)
    try:
        subprocess.run(
            [
                "exiftool",
                "-overwrite_original",
                f"-FileCreateDate={create_time}",
                f"-FileModifyDate={modify_time}",
                str(target_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        pass
    if mtime > 0:
        try:
            os.utime(target_path, (mtime, mtime))
        except OSError:
            pass


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
        _preserve_timestamps(target_path, row.btime, row.mtime)
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
        if not apply_changes:
            summary["skipped"] += 1
            continue
        try:
            entries = list(path.iterdir())
        except OSError:
            summary["skipped"] += 1
            continue
        non_hidden = [entry for entry in entries if not entry.name.startswith(".")]
        if non_hidden:
            summary["skipped"] += 1
            continue
        hidden_dirs = [entry for entry in entries if entry.name.startswith(".") and entry.is_dir()]
        if hidden_dirs:
            summary["skipped"] += 1
            continue
        for entry in entries:
            if entry.name.startswith(".") and entry.is_file():
                try:
                    entry.unlink()
                except OSError:
                    summary["skipped"] += 1
        try:
            path.rmdir()
            summary["deleted"] += 1
        except OSError:
            summary["skipped"] += 1
    return summary
