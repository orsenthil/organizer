from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .scanner import FileInfo


@dataclass
class GroupPlan:
    md5: str
    original: FileInfo
    duplicates: list[FileInfo]
    year: str
    month: str


@dataclass
class PlannedFile:
    md5: str
    file_path: Path
    original_path: Path
    is_original: bool
    year: str
    month: str
    target_path: Path
    action: str


def choose_year_month(btime: float, mtime: float, now: datetime | None = None) -> tuple[str, str]:
    selected = btime or mtime
    if not selected:
        selected = (now or datetime.now()).timestamp()
    date = datetime.fromtimestamp(selected)
    return str(date.year), f"{date.month:02d}"


def build_groups(
    files: list[FileInfo],
    now: datetime | None = None,
) -> list[GroupPlan]:
    groups: dict[str, list[FileInfo]] = {}
    for info in files:
        groups.setdefault(info.md5, []).append(info)
    plans: list[GroupPlan] = []
    for md5, items in groups.items():
        items_sorted = sorted(items, key=lambda info: str(info.path))
        original = items_sorted[0]
        duplicates = items_sorted[1:]
        year, month = choose_year_month(original.btime, original.mtime, now=now)
        plans.append(
            GroupPlan(
                md5=md5,
                original=original,
                duplicates=duplicates,
                year=year,
                month=month,
            )
        )
    return plans


def build_plan_rows(groups: list[GroupPlan], output_root: Path) -> list[PlannedFile]:
    rows: list[PlannedFile] = []
    for group in groups:
        target_dir = output_root / group.year / group.month
        target_path = target_dir / group.original.path.name
        rows.append(
            PlannedFile(
                md5=group.md5,
                file_path=group.original.path,
                original_path=group.original.path,
                is_original=True,
                year=group.year,
                month=group.month,
                target_path=target_path,
                action="keep",
            )
        )
        for index, duplicate in enumerate(group.duplicates, start=1):
            dup_stem = group.original.path.stem
            dup_suffix = group.original.path.suffix
            if index == 1:
                duplicate_name = f"duplicate_{dup_stem}{dup_suffix}"
            else:
                duplicate_name = f"duplicate_{dup_stem}__{index}{dup_suffix}"
            rows.append(
                PlannedFile(
                    md5=group.md5,
                    file_path=duplicate.path,
                    original_path=group.original.path,
                    is_original=False,
                    year=group.year,
                    month=group.month,
                    target_path=target_dir / duplicate_name,
                    action="duplicate",
                )
            )
    return rows
