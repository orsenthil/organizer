from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import os
from pathlib import Path
import re
from typing import Iterable

from PIL import Image
from PyPDF2 import PdfReader


DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
}


@dataclass(frozen=True)
class FileInfo:
    path: Path
    size: int
    md5: str
    btime: float
    ctime: float
    mtime: float
    created_time: float
    created_source: str


def compute_md5(path: Path, chunk_size: int = 1024 * 1024) -> str:
    hasher = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _filter_dirnames(dirnames: list[str], exclude_dirs: set[str]) -> list[str]:
    return [
        name
        for name in dirnames
        if name not in exclude_dirs and not name.startswith(".")
    ]


def _parse_datetime_compact(value: str) -> datetime | None:
    digits = "".join(re.findall(r"\d", value))
    if len(digits) >= 14:
        fmt = "%Y%m%d%H%M%S"
        return datetime.strptime(digits[:14], fmt)
    if len(digits) >= 12:
        fmt = "%Y%m%d%H%M"
        return datetime.strptime(digits[:12], fmt)
    if len(digits) >= 10:
        fmt = "%Y%m%d%H"
        return datetime.strptime(digits[:10], fmt)
    if len(digits) >= 8:
        fmt = "%Y%m%d"
        return datetime.strptime(digits[:8], fmt)
    return None


def _parse_datetime(value: str) -> datetime | None:
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return _parse_datetime_compact(value)


def _metadata_timestamp(path: Path) -> float:
    suffix = path.suffix.lower()
    candidates: list[float] = []
    if suffix == ".pdf":
        try:
            reader = PdfReader(str(path))
            metadata = reader.metadata or {}
            for key in ("/CreationDate", "/ModDate"):
                value = metadata.get(key)
                if not value:
                    continue
                dt = _parse_datetime(str(value))
                if dt:
                    candidates.append(dt.timestamp())
        except Exception:
            pass
    else:
        try:
            image = Image.open(path)
            exif = image.getexif()
            for tag_id in (36867, 36868, 306):
                value = exif.get(tag_id)
                if not value:
                    continue
                if isinstance(value, bytes):
                    try:
                        value = value.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                dt = _parse_datetime(str(value))
                if dt:
                    candidates.append(dt.timestamp())
        except Exception:
            pass
    if not candidates:
        return 0.0
    return min(candidates)


def _choose_created_time(
    meta_time: float,
    btime: float,
    ctime: float,
    mtime: float,
) -> tuple[float, str]:
    candidates: list[tuple[str, float]] = [
        ("metadata", meta_time),
        ("birthtime", btime),
        ("ctime", ctime),
        ("mtime", mtime),
    ]
    valid = [(label, value) for label, value in candidates if value and value > 0]
    if not valid:
        return 0.0, "unknown"
    earliest = min(value for _, value in valid)
    for label, value in valid:
        if value == earliest:
            return earliest, label
    return earliest, "unknown"


def scan_files(root: Path, exclude_dirs: Iterable[str] | None = None) -> list[FileInfo]:
    exclude = set(exclude_dirs or DEFAULT_EXCLUDE_DIRS)
    results: list[FileInfo] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = _filter_dirnames(dirnames, exclude)
        for filename in filenames:
            if filename.startswith("."):
                continue
            path = Path(dirpath) / filename
            if path.is_symlink():
                continue
            try:
                stat_result = path.stat()
            except OSError:
                continue
            if not path.is_file():
                continue
            md5 = compute_md5(path)
            btime = getattr(stat_result, "st_birthtime", 0.0)
            if not btime:
                btime = stat_result.st_ctime
            ctime = stat_result.st_ctime
            mtime = stat_result.st_mtime
            meta_time = _metadata_timestamp(path)
            created_time, created_source = _choose_created_time(
                meta_time=meta_time,
                btime=btime,
                ctime=ctime,
                mtime=mtime,
            )
            results.append(
                FileInfo(
                    path=path,
                    size=stat_result.st_size,
                    md5=md5,
                    btime=btime,
                    ctime=ctime,
                    mtime=mtime,
                    created_time=created_time,
                    created_source=created_source,
                )
            )
    return results
