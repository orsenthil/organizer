## Organizer

Organize synced files into `Year/Month` folders, deduplicate by MD5, and generate a CSV report before making any changes.

### Architecture
The tool is a small CLI with a clear pipeline:
- **Scanner** reads files, hashes content, and resolves the earliest creation timestamp.
- **Planner** groups duplicates by hash and plans target paths.
- **Actions** move files, delete duplicates, and optionally clean empty folders.

Code layout:
- `src/organizer/scanner.py`: file discovery, MD5, and timestamp resolution
- `src/organizer/planner.py`: grouping and output path planning
- `src/organizer/actions.py`: moves, deletes, timestamp preservation
- `src/organizer/cli.py`: CLI arguments and report generation

### Technologies used
- [ExifTool](https://exiftool.org/) for robust metadata timestamps
- [Exif](https://en.wikipedia.org/wiki/Exif) and [PDF](https://en.wikipedia.org/wiki/PDF) metadata parsing
- [MD5](https://en.wikipedia.org/wiki/MD5) for duplicate detection
- [CSV](https://en.wikipedia.org/wiki/Comma-separated_values) for reports
- [PyInstaller](https://pyinstaller.org/) for single-file binaries
- [uv](https://docs.astral.sh/uv/) for dependency management

### What it does
- Scans the current folder (recursively), skipping hidden/system folders.
- Computes MD5 to find duplicates. Keeps the first path and marks the rest for deletion.
- Derives Year/Month from earliest of metadata (ExifTool when available, else EXIF/PDF), birthtime, ctime, mtime.
- Generates a CSV report. By default, it is a dry run.

### Install and run (uv)
From the project root:

```bash
uv sync
uv run organizer
```

ExifTool is required (used to read original creation timestamps). Install it first:

```bash
brew install exiftool
```

### Common usage
Show version and build time:

```bash
uv run organizer --version
```
Dry run (CSV only, no changes) in the current directory:

```bash
uv run organizer
```

Apply changes (move originals only):

```bash
uv run organizer --organize /path/to/folder
```

Organize into a separate output folder:

```bash
uv run organizer --organize /path/to/folder --output-root /path/to/output
```

Delete duplicates only:

```bash
uv run organizer --delete-duplicates /path/to/folder
```

Delete empty folders in current working directory:

```bash
uv run organizer --delete-empty-folders
```

Custom report path (dry run):

```bash
uv run organizer --report /path/to/report.csv
```

### Build a single-file binary (PyInstaller)
```bash
uv run --extra build pyinstaller --onefile -n organizer src/organizer/cli.py
```

The binary will be created in `dist/organizer`.

### Tests
```bash
uv run --extra test pytest
```

### CSV output
The CSV includes:
- `md5`: file hash
- `file_path`: path of the file in the scan
- `original_path`: path of the kept file for that hash
- `is_original`: yes/no
- `year`, `month`
- `created_source`: exiftool:<tag>/metadata/birthtime/ctime/mtime/unknown
- `target_path`: destination for the kept file
- `action`: keep/duplicate

### Safety
- Default behavior is a **dry run** (CSV only).
- Use either `--organize` or `--delete-duplicates` to apply changes.
- Organizing and deleting are separate runs.
