from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
import shutil
import sys

from organizer.actions import delete_duplicates, delete_empty_folders, organize_files
from organizer import __build_time__, __version__
from organizer.planner import build_groups, build_plan_rows, GroupPlan, PlannedFile
from organizer.scanner import scan_files


def _open_report(report_path: Path, fieldnames: list[str]) -> tuple[csv.DictWriter, bool, object]:
    mode = "w"
    write_header = True
    if report_path.exists():
        try:
            with report_path.open("r", encoding="utf-8", newline="") as handle:
                first_line = handle.readline().strip()
            if first_line == ",".join(fieldnames):
                mode = "a"
                write_header = False
        except OSError:
            pass
    handle = report_path.open(mode, newline="", encoding="utf-8")
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    return writer, write_header, handle


def _write_csv(report_path: Path, rows: list[PlannedFile]) -> None:
    fieldnames = [
        "md5",
        "file_path",
        "original_path",
        "is_original",
        "year",
        "month",
        "created_source",
        "target_path",
        "action",
    ]
    writer, write_header, handle = _open_report(report_path, fieldnames)
    with handle:
        if write_header:
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
                    "created_source": row.created_source,
                    "target_path": str(row.target_path),
                    "action": row.action,
                }
            )


def _write_delete_empty_report(report_path: Path, summary: dict[str, int]) -> None:
    fieldnames = [
        "md5",
        "file_path",
        "original_path",
        "is_original",
        "year",
        "month",
        "created_source",
        "target_path",
        "action",
    ]
    writer, write_header, handle = _open_report(report_path, fieldnames)
    with handle:
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "md5": "",
                "file_path": "",
                "original_path": "",
                "is_original": "",
                "year": "",
                "month": "",
                "created_source": "",
                "target_path": "",
                "action": f"delete_empty_folders deleted={summary.get('deleted', 0)} skipped={summary.get('skipped', 0)}",
            }
        )


def _build_rows(groups: list[GroupPlan], output_root: Path) -> list[PlannedFile]:
    return build_plan_rows(groups, output_root=output_root)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Organize duplicate files into Year/Month folders."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"organizer {__version__} (built {__build_time__})",
    )
    parser.add_argument(
        "--report",
        default="duplicate_report.csv",
        help="CSV report path (default: duplicate_report.csv).",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Output folder to organize into (default: same as --organize PATH).",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--organize",
        metavar="PATH",
        help="Organize files under PATH into Year/Month folders.",
    )
    mode_group.add_argument(
        "--delete-duplicates",
        metavar="PATH",
        help="Delete duplicates under PATH (originals remain in place).",
    )
    parser.add_argument(
        "--delete-empty-folders",
        action="store_true",
        help="Delete empty folders in the current working directory.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if shutil.which("exiftool") is None:
        print("ExifTool is required but not installed. Install `exiftool` and retry.")
        return 2
    if args.organize:
        root = Path(args.organize).resolve()
        output_root = Path(args.output_root).resolve() if args.output_root else root
    elif args.delete_duplicates:
        root = Path(args.delete_duplicates).resolve()
        output_root = root
    else:
        root = Path.cwd().resolve()
        output_root = Path(args.output_root).resolve() if args.output_root else root
    report_path = Path(args.report).resolve()

    if args.delete_empty_folders:
        empty_summary = delete_empty_folders(Path.cwd(), apply_changes=True)
        _write_delete_empty_report(report_path, empty_summary)
        print(f"CSV report written to: {report_path}")
        print(
            "Empty folders cleanup. "
            f"Deleted: {empty_summary['deleted']}, Skipped: {empty_summary['skipped']}."
        )
        if not args.organize and not args.delete_duplicates:
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

    if not args.organize and not args.delete_duplicates:
        print("Dry run only. Use --organize or --delete-duplicates to apply changes.")
        return 0

    if args.organize:
        summary = organize_files(rows, apply_changes=True)
        print(f"Done. Moved: {summary['moved']}, Skipped: {summary['skipped']}.")
    elif args.delete_duplicates:
        summary = delete_duplicates(rows, apply_changes=True)
        print(f"Done. Deleted: {summary['deleted']}, Skipped: {summary['skipped']}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
