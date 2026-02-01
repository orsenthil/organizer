from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
import sys

from organizer.actions import delete_duplicates, delete_empty_folders, organize_files
from organizer.planner import build_groups, build_plan_rows, GroupPlan, PlannedFile
from organizer.scanner import scan_files


def _write_csv(report_path: Path, rows: list[PlannedFile]) -> None:
    fieldnames = [
        "md5",
        "file_path",
        "original_path",
        "is_original",
        "year",
        "month",
        "target_path",
        "action",
    ]
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "md5": row.md5,
                    "file_path": str(row.file_path),
                    "original_path": str(row.original_path),
                    "is_original": "yes" if row.is_original else "no",
                    "year": row.year,
                    "month": row.month,
                    "target_path": str(row.target_path),
                    "action": row.action,
                }
            )


def _build_rows(groups: list[GroupPlan], output_root: Path) -> list[PlannedFile]:
    return build_plan_rows(groups, output_root=output_root)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Organize duplicate files into Year/Month folders."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root folder to scan (default: current folder).",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Root folder to organize into (default: same as --root).",
    )
    parser.add_argument(
        "--report",
        default="duplicate_report.csv",
        help="CSV report path (default: duplicate_report.csv).",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--organize",
        action="store_true",
        help="Move unique files into Year/Month/Topic folders.",
    )
    mode_group.add_argument(
        "--delete",
        action="store_true",
        help="Delete duplicate files (originals remain in place).",
    )
    parser.add_argument(
        "--delete-empty-folders",
        action="store_true",
        help="Delete empty folders in the current working directory.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.root).resolve()
    output_root = Path(args.output_root).resolve() if args.output_root else root
    report_path = Path(args.report).resolve()

    if args.delete_empty_folders:
        empty_summary = delete_empty_folders(Path.cwd(), apply_changes=True)
        print(
            "Empty folders cleanup. "
            f"Deleted: {empty_summary['deleted']}, Skipped: {empty_summary['skipped']}."
        )
        if not args.organize and not args.delete:
            return 0

    print(f"Scanning files under: {root}")
    files = scan_files(root)
    if not files:
        print("No files found to process.")
        return 0

    groups = build_groups(files, now=datetime.now())
    rows = _build_rows(groups, output_root=output_root)
    _write_csv(report_path, rows)
    print(f"CSV report written to: {report_path}")

    if not args.organize and not args.delete:
        print("Dry run only. Use --organize or --delete to apply changes.")
        return 0

    if args.organize:
        summary = organize_files(rows, apply_changes=True)
        print(f"Done. Moved: {summary['moved']}, Skipped: {summary['skipped']}.")
    elif args.delete:
        summary = delete_duplicates(rows, apply_changes=True)
        print(f"Done. Deleted: {summary['deleted']}, Skipped: {summary['skipped']}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
