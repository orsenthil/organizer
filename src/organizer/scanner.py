from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from typing import Iterable


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
    ctime: float
    mtime: float


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
            results.append(
                FileInfo(
                    path=path,
                    size=stat_result.st_size,
                    md5=md5,
                    ctime=stat_result.st_ctime,
                    mtime=stat_result.st_mtime,
                )
            )
    return results
