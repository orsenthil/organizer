from __future__ import annotations

from datetime import datetime
from pathlib import Path

from organizer.planner import build_groups, build_plan_rows, choose_year_month
from organizer.actions import delete_empty_folders
from organizer.scanner import FileInfo, compute_md5
from organizer.topic import infer_topic_from_filename, infer_topic_from_text


def test_compute_md5(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("hello world", encoding="utf-8")
    result = compute_md5(sample)
    assert result == "5eb63bbbe01eeed093cb22bb8f5acdc3"


def test_infer_topic_from_text() -> None:
    text = "Project roadmap project milestones and timeline for project."
    topic = infer_topic_from_text(text)
    assert "project" in topic.lower()


def test_infer_topic_from_filename() -> None:
    topic = infer_topic_from_filename(Path("Quarterly_Report_2023.pdf"))
    assert "quarterly" in topic.lower()


def test_choose_year_month_fallback() -> None:
    fixed = datetime(2022, 3, 15, 10, 0, 0)
    year, month = choose_year_month(0.0, 0.0, now=fixed)
    assert year == "2022"
    assert month == "03"


def test_build_groups_and_rows(tmp_path: Path) -> None:
    file_a = tmp_path / "a.txt"
    file_b = tmp_path / "b.txt"
    file_a.write_text("same", encoding="utf-8")
    file_b.write_text("same", encoding="utf-8")
    md5 = compute_md5(file_a)
    info_a = FileInfo(path=file_a, size=4, md5=md5, ctime=1.0, mtime=1.0)
    info_b = FileInfo(path=file_b, size=4, md5=md5, ctime=1.0, mtime=1.0)
    groups = build_groups([info_a, info_b])
    rows = build_plan_rows(groups, output_root=tmp_path)
    assert len(groups) == 1
    assert len(rows) == 2
    assert any(row.action == "keep" for row in rows)
    assert any(row.action == "delete" for row in rows)


def test_delete_empty_folders(tmp_path: Path) -> None:
    (tmp_path / "keep" / "nested").mkdir(parents=True)
    (tmp_path / "keep" / "nested" / "file.txt").write_text("data", encoding="utf-8")
    empty_dir = tmp_path / "empty" / "nested"
    empty_dir.mkdir(parents=True)

    summary = delete_empty_folders(tmp_path, apply_changes=True)
    assert summary["deleted"] >= 1
    assert (tmp_path / "keep" / "nested").exists()
