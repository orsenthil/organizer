from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
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
        try:
            return datetime.strptime(digits[:14], fmt)
        except ValueError:
            return None
    if len(digits) >= 12:
        fmt = "%Y%m%d%H%M"
        try:
            return datetime.strptime(digits[:12], fmt)
        except ValueError:
            return None
    if len(digits) >= 10:
        fmt = "%Y%m%d%H"
        try:
            return datetime.strptime(digits[:10], fmt)
        except ValueError:
            return None
    if len(digits) >= 8:
        fmt = "%Y%m%d"
        try:
            return datetime.strptime(digits[:8], fmt)
        except ValueError:
            return None
    return None


def _parse_datetime(value: str) -> datetime | None:
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return _parse_datetime_compact(value)
    except ValueError:
        return None


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


def _exiftool_timestamp(path: Path) -> tuple[float, str]:
    try:
        result = subprocess.run(
            [
                "exiftool",
                "-j",
                "-d",
                "%Y-%m-%d %H:%M:%S",
                "-DateTimeOriginal",
                "-CreateDate",
                "-CreationDate",
                "-ModifyDate",
                "-FileCreateDate",
                "-FileModifyDate",
                "-FileInodeChangeDate",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return 0.0, "exiftool"
    if result.returncode != 0 or not result.stdout:
        return 0.0, "exiftool"
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return 0.0, "exiftool"
    if not payload:
        return 0.0, "exiftool"
    data = payload[0]
    candidates: list[tuple[str, float]] = []
    for key in (
        "DateTimeOriginal",
        "CreateDate",
        "CreationDate",
        "ModifyDate",
        "FileCreateDate",
        "FileModifyDate",
        "FileInodeChangeDate",
    ):
        value = data.get(key)
        if not value:
            continue
        dt = _parse_datetime(str(value))
        if dt:
            candidates.append((key, dt.timestamp()))
    if not candidates:
        return 0.0, "exiftool"
    key, earliest = min(candidates, key=lambda item: item[1])
    return earliest, f"exiftool:{key}"


def _choose_created_time(
    meta_time: float,
    meta_source: str,
    btime: float,
    ctime: float,
    mtime: float,
) -> tuple[float, str]:
    candidates: list[tuple[str, float]] = [
        (meta_source, meta_time),
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
            exif_time, exif_source = _exiftool_timestamp(path)
            if exif_time:
                meta_time = exif_time
                meta_source = exif_source
            else:
                meta_time = _metadata_timestamp(path)
                meta_source = "metadata" if meta_time else "metadata"
            created_time, created_source = _choose_created_time(
                meta_time=meta_time,
                meta_source=meta_source,
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
